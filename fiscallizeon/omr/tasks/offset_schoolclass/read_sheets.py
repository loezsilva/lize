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
from fiscallizeon.students.models import Student


def read_sheet(file_path, exam, category):
    omr_marker_path = os.path.join(settings.BASE_DIR, 'fiscallizeon', 'core', 'static', 'omr_marker.jpg')
    json_obj = category.get_exam_json(exam)

    if settings.DEBUG:
        print(f'Exam JSON | EXAM {exam.pk}:')
        print(json_obj)
    return process_file(file_path, json_obj, omr_marker_path)

@app.task(compression='gzip')
def read_sheets(upload_id, omr_url, page_number, students_class_count):
    omr_upload = OMRUpload.objects.using('default').get(pk=upload_id)
    omr_category = OMRCategory.objects.get(sequential=OMRCategory.OFFSET_SCHOOLCLASS)
    client = omr_upload.user.get_clients().first()
    school_class = omr_upload.school_class

    student = Student(
        client=client,
        name=f'Aluno {students_class_count + page_number} | {school_class.name} - {school_class.coordination.unity.name}',
        enrollment_number=f'{str(omr_upload.pk)[:8]}-{page_number}',
    )
    student.save(skip_hooks=True)
    school_class.students.add(student)

    application_student = ApplicationStudent.objects.create(
        student=student,
        application=omr_upload.application,
        is_omr=True,
    )

    try:
        tmp_file = download_spaces_image(omr_url)

        if omr_upload.gamma_option and omr_upload.gamma_option > 1:
            image = cv2.imread(tmp_file)
            adjusted_image = np.uint8(((image / 255.0) ** float(omr_upload.gamma_option)) * 255.0)
            cv2.imwrite(tmp_file, adjusted_image)

        #Cortando área branca
        image = cv2.imread(tmp_file)
        h, w = image.shape[:2]
        cropped_image = image[:int(h - h/10), :w]
        cv2.imwrite(tmp_file, cropped_image)

        answer = read_sheet(tmp_file, application_student.application.exam, omr_category)
        os.remove(tmp_file)
        if settings.DEBUG:
            print(f'Answer | ApplicationStudent {application_student.pk}:')
            print(answer)
    except Exception as e:
        print(f"Erro na leitura das respostas: {e}")

    omr_student = OMRStudents.objects.filter(
        upload=omr_upload,
        application_student=application_student
    ).first()

    if not omr_student:
        omr_student = OMRStudents.objects.create(
            upload=omr_upload,
            application_student=application_student,
            successful_questions_count=0,
            scan_image=omr_url,
        )

    answer['category'] = omr_category.sequential
    answer['instance'] = str(application_student.pk)
    answer['file_url'] = omr_url

    return (upload_id, answer)
