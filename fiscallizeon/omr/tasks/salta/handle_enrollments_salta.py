import os

from django.db.models import F, Value
from django.db.models.functions import Replace
from django.core.files.uploadedfile import UploadedFile

from fiscallizeon.celery import app
from fiscallizeon.omr.functions.main import process_file
from fiscallizeon.omr.utils import download_spaces_image
from fiscallizeon.omr.models import OMRUpload, OMRError, OMRCategory
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.students.models import Student


@app.task
def handle_enrollments_salta(args):
    upload_id, omr_files = args

    omr_upload = OMRUpload.objects.using('default').get(pk=upload_id)
    omr_category = OMRCategory.objects.get(sequential=9)

    uploads_data = []

    for page_number, sheet_file in enumerate(sorted(omr_files), 1):
        sheet_data = {
            'path': sheet_file,
            'page_number': page_number,
        }

        try:
            omr_marker_path = omr_category.get_omr_marker_path()
            json_obj = omr_category.dettached_template
            tmp_file = download_spaces_image(sheet_file)
            answer = process_file(tmp_file, json_obj, omr_marker_path)
            enrollment_number = answer.get('Roll', None)
            external_code = answer.get('Exam', None)
        except Exception:
            OMRError.objects.create(
                upload=omr_upload,
                omr_category=omr_category,
                error_image=UploadedFile(
                    file=open(tmp_file, 'rb')
                ),
                category=OMRError.MARKERS_NOT_FOUND,
                page_number=page_number,
            )
            continue

        try:
            application = Application.objects.using("default").filter(
                exam__external_code=external_code
            ).first()
        except Exception as e:
            print(e)
            OMRError.objects.create(
                upload=omr_upload,
                omr_category=omr_category,
                error_image=UploadedFile(
                    file=open(tmp_file, 'rb')
                ),
                category=OMRError.STUDENT_NOT_FOUND,
                page_number=page_number,
            )
            continue

        if not enrollment_number:
            OMRError.objects.create(
                upload=omr_upload,
                omr_category=omr_category,
                error_image=UploadedFile(
                    file=open(tmp_file, 'rb')
                ),
                category=OMRError.STUDENT_NOT_FOUND,
                application=application,
                page_number=page_number,
            )
            continue
        
        student = Student.objects.annotate(
            enrollment_number_numeric=Replace(
                F('enrollment_number'), Value('-'), Value('')
            )
        ).filter(
            client__in=omr_upload.user.get_clients(),
            enrollment_number_numeric=enrollment_number
        )

        if (not student or student.count() > 1):
            OMRError.objects.create(
                upload=omr_upload,
                omr_category=omr_category,
                error_image=UploadedFile(
                    file=open(tmp_file, 'rb')
                ),
                category=OMRError.STUDENT_NOT_FOUND,
                application=application,
                page_number=page_number,
            )
            continue

        if not application:
            OMRError.objects.create(
                upload=omr_upload,
                omr_category=omr_category,
                error_image=UploadedFile(
                    file=open(tmp_file, 'rb')
                ),
                category=OMRError.STUDENT_NOT_FOUND,
                student=student.first(),
                page_number=page_number,
            )
            continue

        application_student = ApplicationStudent.objects.using("default").filter(
            student=student.first(),
            application=application,
        ).first()

        if not application_student:
            application_student = ApplicationStudent.objects.create(
                student=student.first(),
                application=application,
            )

        application_student.is_omr = True
        application_student.save()

        sheet_data['instance'] = str(application_student.pk)
        uploads_data.append(sheet_data)
        os.remove(tmp_file)

    return (upload_id, uploads_data)