import os
import shutil
import uuid

import requests
from celery import chain

from django.core.management.base import BaseCommand
from django.db.models import Count

from fiscallizeon.omr.models import OMRStudents, OMRDiscursiveScan, OMRDiscursiveError
from fiscallizeon.omr.tasks.discursive.crop_answer_area import crop_answer_area
from fiscallizeon.omr.tasks.discursive.handle_discursive_answers import handle_discursive_answers
from fiscallizeon.omr.tasks.finish_processing import finish_processing

class Command(BaseCommand):
    help = 'Corrige problema em uploads de discursivas com mais de uma página'
    RESULTS_DIR = '/code/tmp/fix-discursives'

    def handle(self, *args, **kwargs):
        os.makedirs(self.RESULTS_DIR, exist_ok=True)

        omr_students = OMRStudents.objects.filter(
            created_at__year=2023
        ).annotate(
            discursive_pages=Count('omrdiscursivescan', distinct=True)
        ).filter(discursive_pages__gt=0)

        OMRDiscursiveError.objects.filter(
            upload__in=omr_students.values('upload')
        ).update(is_solved=True)

        print(f"### OMRStudents para atualizar: {omr_students.count()}")

        for omr_student in omr_students:
            args = []
            discursive_scans = OMRDiscursiveScan.objects.filter(omr_student=omr_student)
            print(f"- Ajustando {omr_student.application_student.student.name} | Aplicação: {omr_student.application_student.application_id} | OMRStudent: {omr_student.pk} | Exam: {omr_student.application_student.application.exam_id}")
            print("#### Páginas encontradas: ", discursive_scans.count())
            for i, scan in enumerate(discursive_scans):
                with requests.get(scan.upload_image.url, stream=True) as r:
                    tmp_file = os.path.join(self.RESULTS_DIR, f'{uuid.uuid4()}.jpg')
                    with open(tmp_file, 'wb') as f:
                        shutil.copyfileobj(r.raw, f)

                    args.append({
                        "page_number": i,
                        "operation_type":"S",
                        "sequential": 8,
                        "randomization_version": None,
                        "file_path": tmp_file,
                        "object_id": omr_student.application_student_id,
                        "ignore_omr_scan": True,
                        "ignore_question_corrected": True,
                    })

            chain(
                crop_answer_area.si([omr_student.upload_id, args]),
                handle_discursive_answers.s(),
                finish_processing.si(omr_student.upload_id),
            )()

            with open(os.path.join(self.RESULTS_DIR, 'updated.txt'), 'a') as f:
                f.write(str(omr_student.pk))
                f.write('\n')
        
        print(f'Processo finalizado')