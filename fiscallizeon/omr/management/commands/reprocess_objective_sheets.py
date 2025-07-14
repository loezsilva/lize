import os
import shutil
import uuid
import datetime

import requests

from django.core.management.base import BaseCommand
from django.conf import settings

from fiscallizeon.omr.models import OMRStudents, OMRCategory
from fiscallizeon.omr.utils import process_header_qr, download_spaces_image
from fiscallizeon.omr.functions.main import process_file
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.omr.tasks.handle_answers import create_option_answers

class Command(BaseCommand):
    help = 'Reprocessa apenas folhas objetivas randomizadas de um caderno'

    def read_sheet(self, file_path, exam, category):
        omr_marker_path = os.path.join(settings.BASE_DIR, 'fiscallizeon', 'core', 'static', 'omr_marker.jpg')
        json_obj = category.get_exam_json(exam)

        if settings.DEBUG:
            print(f'Exam JSON | EXAM {exam.pk}:')
            print(json_obj)
        return process_file(file_path, json_obj, omr_marker_path)

    # def add_arguments(self, parser):
    #     parser.add_argument('exam_pk', type=str, help='ID da prova para processar as folhas objetivas')

    def handle(self, *args, **kwargs):
        print(f'Processo iniciado às ', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), '\n\n')
        apps = ApplicationStudent.objects.filter(
            student__client="a2b1158b-367a-40a4-8413-9897057c8aa2",
            read_randomization_version=0,
            application__exam__name__istartswith="p3",
            created_at__year=2025,
            is_omr=True
        ).distinct()

        omr_students = OMRStudents.objects.filter(
            application_student__in=apps,
            scan_image__isnull=False,
        ).exclude(
            scan_image__exact=''
        )

        print(f'Encontrados {omr_students.count()} alunos com divergências')

        for omr_student in omr_students:
            tmp_file = download_spaces_image(str(omr_student.scan_image))
            if not tmp_file:
                print(f'Arquivo {omr_student.scan_image} não encontrado')
                continue
            qr_content, _ = process_header_qr(tmp_file)

            if not qr_content:
                print(f'QR code não reconhecido para {omr_student.scan_image}')
                continue
            
            try:
                operation_type, sequential, object_id  = qr_content.split(':')
                sequential = int(sequential)
                object_id = uuid.UUID(object_id)
            except Exception as e:
                print(f'QR code inválido: {qr_content} para {omr_student.scan_image}')
                continue
            
            if operation_type[0] not in ['S', 'A', 'R']:
                print(f'Sequencial {operation_type} inválido para {omr_student.scan_image}')
                continue

            try:
                randomization_version = None
                if operation_type[0] == 'R':
                    randomization_version = operation_type[1:]
                
                if not randomization_version:
                    print(f'Versãod e randomização não identificada em {omr_student.scan_image.url}')
                    continue
            except Exception as e:
                print(f'Erro ao processar operação {operation_type} para {omr_student.scan_image.url}: {e}')
                continue

            omr_category = OMRCategory.objects.get(sequential=OMRCategory.FISCALLIZE)
            application_student = omr_student.application_student

            try:
                answer = self.read_sheet(tmp_file, application_student.application.exam, omr_category)
            except Exception as e:
                print(f'Erro ao ler folha para {omr_student.scan_image.url}: {e}')
                continue

            os.remove(tmp_file)

            answer['instance'] = str(application_student.pk)
            answer['randomization_version'] = randomization_version

            try:
                application_student, questions_count = create_option_answers(answer)
                application_student.read_randomization_version = randomization_version
                application_student.save()
                print(f'{questions_count} questoes processadas para {application_student.student.name}. Versão de randomização lida no QR: {randomization_version}')
            except Exception as e:
                print(f'Erro ao processar respostas para {application_student}: {e}')
                continue

        print(f'\n\nProcesso finalizado às ', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))