import cv2
import numpy as np

import os
from datetime import datetime


from django.conf import settings
from django.utils import timezone

from fiscallizeon.celery import app
from fiscallizeon.omr.utils import download_spaces_image
from fiscallizeon.omr.functions.main import process_file
from fiscallizeon.omr.models import OMRUpload, OMRError, OMRCategory, OMRStudents
from fiscallizeon.applications.models import ApplicationStudent


def read_sheet(file_path, exam, category):
    omr_marker_path = os.path.join(settings.BASE_DIR, 'fiscallizeon', 'core', 'static', 'omr_marker.jpg')
    json_obj = category.get_exam_json(exam)

    if settings.DEBUG:
        print(f'Exam JSON | EXAM {exam.pk}:')
        print(json_obj)
    return process_file(file_path, json_obj, omr_marker_path)

@app.task(compression='gzip')
def read_sheets_directory_fiscallize(upload_id, sheet):
    omr_upload = OMRUpload.objects.using('default').get(pk=upload_id)
    omr_category = OMRCategory.objects.get(sequential=sheet['sequential'])

    page_number = sheet.get('page_number', 0)
    randomization_version =  sheet['randomization_version']
    application_student_pk = sheet['object_id']

    application_student = ApplicationStudent.objects.filter(
        pk=application_student_pk
    ).order_by('created_at').first()

    if application_student:
        if not application_student.student.client_id in omr_upload.user.get_clients_cache():
            omr_upload.append_processing_log(f'Aplicação ou aluno não pertence a instituição, aplicação: {application_student_pk} - Página {page_number}')
            return
        try:
            tmp_file = download_spaces_image(sheet['file_path'])

            if application := omr_upload.application:
                application_student.application = application
                application_student.save()

            if omr_upload.gamma_option and omr_upload.gamma_option > 1:
                image = cv2.imread(tmp_file)
                adjusted_image = np.uint8(((image / 255.0) ** float(omr_upload.gamma_option)) * 255.0)
                cv2.imwrite(tmp_file, adjusted_image)

            answer = read_sheet(tmp_file, application_student.application.exam, omr_category)
            os.remove(tmp_file)
            if settings.DEBUG:
                print(f'Answer | ApplicationStudent {application_student_pk}:')
                print(answer)
        except Exception as e:
            print(f"Erro na leitura das respostas: {e}")
            try:
                application_student.read_randomization_version = int(randomization_version)
            except Exception as e:
                print(f"Versão de randomização {randomization_version} não pôde ser atribuída ao application_student {application_student.pk}")
            
            application_student.is_omr = True
            application_student.save()

            omr_student = OMRStudents.objects.filter(
                upload=omr_upload,
                application_student=application_student
            ).first()

            if not omr_student:
                omr_student = OMRStudents.objects.create(
                    upload=omr_upload,
                    application_student=application_student,
                    successful_questions_count=0,
                    scan_image=sheet['file_path'],
                )

            if omr_error_id := sheet.get('omr_error_id', None):
                omr_error = OMRError.objects.get(pk=omr_error_id)
                omr_error.is_solved = True
                omr_error.save()
            return

        answer['category'] = omr_category.sequential
        answer['instance'] = str(application_student_pk)
        answer['file_url'] = sheet['file_path']
        answer['randomization_version'] = randomization_version

        if omr_error_id := sheet.get('omr_error_id', None):
            omr_error = OMRError.objects.get(pk=omr_error_id)
            omr_error.is_solved = True
            omr_error.save()

    else:
        OMRError.objects.create(
            upload=omr_upload,
            omr_category=omr_category,
            application=omr_upload.application,
            error_image=sheet['file_path'],
            category=OMRError.STUDENT_NOT_FOUND,
            page_number=page_number,
            randomization_version=randomization_version or 0,
        )
        return None

    return (upload_id, answer)
