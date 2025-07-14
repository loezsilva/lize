import os
import shutil

import requests

from django.conf import settings

from fiscallizeon.celery import app
from fiscallizeon.omr.models import OMRUpload, OMRError
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.students.models import Student


@app.task
def process_omr_errors_sesi(omr_upload_id, omr_error_list):
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

        sheet_data = {
            'path': str(omr_error.error_image),
            'instance': str(application_student.pk),
            'page_number': omr_fix.get('page_number', 0),
            'omr_error_id': str(omr_error.pk),
        }

        sheets_data.append(sheet_data)

    return (omr_upload.pk, sheets_data)
