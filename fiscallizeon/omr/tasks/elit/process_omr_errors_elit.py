import os
import shutil

import requests

from django.conf import settings

from fiscallizeon.celery import app
from fiscallizeon.omr.models import OMRUpload, OMRError
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.students.models import Student


@app.task
def process_omr_errors_elit(omr_upload_id, omr_error_list):
    omr_upload = OMRUpload.objects.get(pk=omr_upload_id)
    sheets_data = []

    for omr_fix in omr_error_list:
        omr_error = OMRError.objects.using('default').get(pk=omr_fix.get('omr_error'))
        application = Application.objects.get(pk=omr_fix.get('application'))
        student = Student.objects.get(pk=omr_fix.get('student'))

        application_student = ApplicationStudent.objects.using('default').filter(
            application__exam=application.exam,
            student=student,
        ).order_by('created_at').first()
            
        if not application_student:
            application_student = ApplicationStudent.objects.create(
                application=application,
                student=student
            )

        application_student.is_omr = True
        application_student.save()

        with requests.get(omr_error.error_image.url, stream=True) as response:
            upload_dir = os.path.join(settings.OMR_UPLOAD_DIR, str(omr_upload_id), 'errors')
            os.makedirs(upload_dir, exist_ok=True)
            error_filepath = os.path.join(upload_dir, f'{omr_error.pk}.jpg')
            with open(error_filepath, "wb") as f:
                shutil.copyfileobj(response.raw, f)

        sheet_data = {
            'image_path': error_filepath,
            'application_student_pk': str(application_student.pk),
            'omr_error_id': str(omr_error.pk),
        }

        sheets_data.append(sheet_data)

    return (omr_upload.pk, sheets_data)
