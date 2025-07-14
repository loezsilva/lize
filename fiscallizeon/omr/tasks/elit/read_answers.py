import os
import gzip
import json
import copy
import base64

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from fiscallizeon.celery import app
from fiscallizeon.omr.functions.main import process_file
from fiscallizeon.omr.models import OMRUpload, OMRError, OMRCategory, OMRStudents, OMRDiscursiveScan
from fiscallizeon.applications.models import ApplicationStudent


@app.task(compression='gzip')
def read_answers(args):
    upload_id, uploads_data = args

    answers = []
    omr_upload = OMRUpload.objects.using('default').get(pk=upload_id)
    
    for cropped_image in uploads_data:
        omr_category = OMRCategory.objects.get(sequential=OMRCategory.ELIT)
        application_student_pk = cropped_image['application_student_pk']

        application_student = ApplicationStudent.objects.filter(
            pk=application_student_pk
        ).order_by('created_at').first()

        if application_student:
            json_obj = omr_category.template
            answer = process_file(cropped_image['image_path'], json_obj)
            
            if settings.DEBUG:
                print(f'Answer | ApplicationStudent {application_student_pk}:')
                print(answer)
                
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
                    scan_image=UploadedFile(
                        file=open(cropped_image['image_path'], 'rb')
                    ),
                )

            omr_discursive_scan = OMRDiscursiveScan.objects.filter(
                omr_student=omr_student
            )

            if not omr_discursive_scan:
                OMRDiscursiveScan.objects.create(
                    omr_student=omr_student,
                    upload_image=UploadedFile(
                        file=open(cropped_image['image_path'], 'rb')
                    ),
                )

            answer['category'] = omr_category.sequential
            answer['instance'] = str(application_student_pk)
            answer['file_url'] = cropped_image['image_path']

            if omr_error_id := cropped_image.get('omr_error_id', None):
                omr_error = OMRError.objects.get(pk=omr_error_id)
                omr_error.is_solved = True
                omr_error.save()

            answers.append(answer)
        else:
            omr_upload.append_processing_log(f'Aluno/aplicação não encontrado {application_student_pk}')

    gziped_answers = gzip.compress(bytes(json.dumps(answers), 'utf-8'))
    return (upload_id, gziped_answers)
