import os
import shutil

import requests

from django.conf import settings

from fiscallizeon.celery import app
from fiscallizeon.omr.models import OMRUpload, OMRError
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.students.models import Student


@app.task
def process_data_without_qr(omr_upload_id, omr_error_list):
    omr_upload = OMRUpload.objects.get(pk=omr_upload_id)
    sheets_data = []

    for omr_fix in omr_error_list:
        omr_error = OMRError.objects.using('default').get(pk=omr_fix.get('omr_error'))
        application = Application.objects.get(pk=omr_fix.get('application'))
        student = Student.objects.get(pk=omr_fix.get('student'))

        try:
            omr_category_sequential = int(omr_fix.get('omr_category'))
        except:
            omr_category_sequential = omr_fix.get('omr_category')

        application_student = ApplicationStudent.objects.using('default').filter(
            application__exam=application.exam,
            student=student,
        ).order_by('created_at').first()
            
        if not application_student:
            application_student = ApplicationStudent.objects.create(
                application=application,
                student=student
            )
            omr_fix['randomization_version'] = 0

        application_student.is_omr = True
        application_student.save()

        sheet_data = {
            'randomization_version': None
        }

        if (randomization_version := omr_fix.get('randomization_version', 0)) > 0:
            sheet_data['randomization_version'] = randomization_version

        sheet_data['operation_type'] = 'S'
        sheet_data['sequential'] = omr_category_sequential
        sheet_data['randomization_version'] = randomization_version
        sheet_data['file_path'] = str(omr_error.error_image)
        sheet_data['object_id'] = str(application_student.pk)
        sheet_data['omr_error_id'] = str(omr_error.pk)
        sheet_data['page_number'] = omr_fix.get('page_number', 0)

        sheets_data.append(sheet_data)

    return (omr_upload.pk, sheets_data)
