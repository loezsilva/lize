import os

from django.conf import settings
from django.db.models import F, Value
from django.db.models.functions import Replace

from fiscallizeon.celery import app
from fiscallizeon.omr.utils import download_spaces_image
from fiscallizeon.omr.functions.main import process_file
from fiscallizeon.omr.models import OMRUpload, OMRError, OMRCategory
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.students.models import Student
from fiscallizeon.clients.models import Client

def _create_omr_error(omr_upload, omr_category, error_image, page_number, application=None, error_category=OMRError.STUDENT_NOT_FOUND):
    OMRError.objects.create(
        upload=omr_upload,
        omr_category=omr_category,
        error_image=error_image,
        category=error_category,
        page_number=page_number,
        application=application,
    )

def read_sheet(file_path, category):
    omr_marker_path = os.path.join(settings.BASE_DIR, 'fiscallizeon', 'core', 'static', 'omr_marker.jpg')
    json_obj = category.dettached_template
    return process_file(file_path, json_obj, omr_marker_path)

@app.task
def handle_avulse_sheets(args):
    upload_id, uploads_data = args

    omr_upload = OMRUpload.objects.using('default').get(pk=upload_id)

    for sheet in uploads_data:
        object_id = sheet['object_id']
        page_number = sheet['page_number']
        sequential = sheet['sequential']

        if sheet['operation_type'] != 'A':
            continue

        try:
            omr_category = OMRCategory.objects.get(sequential=sequential)
            if sequential == OMRCategory.OFFSET_1:
                instance = Client.objects.filter(pk=object_id).first()
            else:
                instance = Application.objects.filter(pk=object_id).first()
        except Exception as e:
            print(e)
            instance = None

        if sequential not in [OMRCategory.FISCALLIZE, OMRCategory.HYBRID_025, OMRCategory.OFFSET_1]:
            omr_category = OMRCategory.objects.get(sequential=sequential)
            _create_omr_error(omr_upload, omr_category, sheet['file_path'], page_number, application=omr_upload.application or instance)
            continue

        if not instance or not omr_upload.application:
            error_category = OMRError.QR_UNRECOGNIZED if sequential == OMRCategory.OFFSET_1 else OMRError.APPLICATION_NOT_FOUND
            _create_omr_error(omr_upload, omr_category, sheet['file_path'], page_number, error_category=error_category)
            continue

        try:
            local_image = download_spaces_image(sheet['file_path'])
            answer = read_sheet(local_image, omr_category)
            enrollment_number = answer.get('Roll', None)
            exam_number = answer.get('Exam', None)
            exam_number = int(exam_number) if exam_number else 0
            os.remove(local_image)

            if settings.DEBUG:
                print("Avulse JSON:", answer)
        except Exception:
            sheet['operation_type'] = 'E'
            OMRError.objects.create(
                upload=omr_upload,
                omr_category=omr_category,
                application=omr_upload.application,
                error_image=sheet['file_path'],
                category=OMRError.MARKERS_NOT_FOUND,
                page_number=page_number,
            )
            continue

        application = omr_upload.application or instance

        if sequential == OMRCategory.OFFSET_1:
            if exam_number:
                application = Application.objects.filter(
                    exam__external_code=exam_number
                ).order_by(
                    'created_at'
                ).first()
            else:
                _create_omr_error(omr_upload, omr_category, sheet['file_path'], page_number, application=application, error_category=OMRError.APPLICATION_NOT_FOUND)

        if not enrollment_number:
            _create_omr_error(omr_upload, omr_category, sheet['file_path'], page_number, application=application)
            continue
        
        student = Student.objects.annotate(
            enrollment_number_numeric=Replace(
                F('enrollment_number'), Value('-'), Value('')
            )
        ).filter(
            client__in=[instance] if sequential == OMRCategory.OFFSET_1 else omr_upload.user.get_clients(),
            enrollment_number_numeric=enrollment_number
        )

        if (not student or student.count() > 1):
            _create_omr_error(omr_upload, omr_category, sheet['file_path'], page_number, application=application)
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
        application_student.save(skip_hooks=True)

        sheet['object_id'] = str(application_student.pk)
        sheet['operation_type'] = 'S'

    return (upload_id, uploads_data)
