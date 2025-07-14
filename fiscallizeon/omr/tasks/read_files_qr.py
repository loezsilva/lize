import os
import uuid

from django.conf import settings

from fiscallizeon.celery import app
from fiscallizeon.omr.utils import process_header_qr, download_spaces_image
from fiscallizeon.omr.models import OMRUpload, OMRError
from fiscallizeon.students.models import Student

@app.task
def read_files_qr(args):
    upload_id, omr_files = args
    uploads_data = []
    omr_upload = OMRUpload.objects.get(pk=upload_id)

    for i, omr_file in enumerate(sorted(omr_files), 1):
        sheet_data = {}
        if omr_upload.ignore_qr_codes:
            OMRError.objects.create(
                upload=omr_upload,
                omr_category=omr_upload.omr_category,
                application=omr_upload.application,
                error_image=omr_file,
                category=OMRError.QR_UNRECOGNIZED,
                page_number=i,
            )
            continue

        tmp_file = download_spaces_image(omr_file)
        qr_content, student_name = process_header_qr(tmp_file)
        os.remove(tmp_file)

        if settings.DEBUG:
            print(f'QR content: {qr_content} | Student name: {student_name}')

        if not qr_content:
            student = None
            if student_name:
                students = Student.objects.filter(
                    name__icontains=student_name,
                    client__in=omr_upload.user.get_clients(),
                )

                if students.count() == 1:
                    student = students.first()

            OMRError.objects.create(
                upload=omr_upload,
                omr_category=omr_upload.omr_category,
                application=omr_upload.application,
                student=student,
                error_image=omr_file,
                category=OMRError.QR_UNRECOGNIZED,
                page_number=i,
            )
            continue
        
        try:
            operation_type, sequential, object_id  = qr_content.split(':')

            if len(operation_type) == 0:
                raise Exception('Operation type not found on QR content')
            
            sequential = int(sequential)
            object_id = uuid.UUID(object_id)
        except Exception as e:
            print(f'Erro na leitura de QR code {e}')
            OMRError.objects.create(
                upload=omr_upload,
                omr_category=omr_upload.omr_category,
                application=omr_upload.application,
                error_image=omr_file,
                category=OMRError.QR_UNRECOGNIZED,
                page_number=i,
            )
            continue

        if operation_type[0] not in ['S', 'A', 'R']:
            print(f"Operation type not found: {operation_type[0]}")
            OMRError.objects.create(
                upload=omr_upload,
                omr_category=omr_upload.omr_category,
                application=omr_upload.application,
                error_image=omr_file,
                category=OMRError.QR_UNRECOGNIZED,
                page_number=i,
            )
            continue

        randomization_version = None
        if operation_type[0] == 'R':
            randomization_version = operation_type[1:]

        sheet_data['page_number'] = i
        sheet_data['operation_type'] = operation_type[0]
        sheet_data['sequential'] = sequential
        sheet_data['randomization_version'] = randomization_version
        sheet_data['file_path'] = omr_file
        sheet_data['object_id'] = object_id
        uploads_data.append(sheet_data)
    
    return (upload_id, uploads_data)
