import os
import glob
import uuid

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from fiscallizeon.celery import app
from fiscallizeon.omr.utils import process_header_qr
from fiscallizeon.omrnps.models import OMRNPSUpload, OMRNPSError

@app.task
def read_files_qr(nps_upload_id):
    uploads_data = []
    upload_base_dir = os.path.join(settings.OMR_UPLOAD_DIR, str(nps_upload_id))

    omr_nps_upload = OMRNPSUpload.objects.get(pk=nps_upload_id)
    omr_nps_files = glob.glob(f'{upload_base_dir}/*.jpg')

    for i, omr_file in enumerate(sorted(omr_nps_files), 1):
        sheet_data = {}
        qr_content, _ = process_header_qr(omr_file)

        if not qr_content:
            OMRNPSError.objects.create(
                upload=omr_nps_upload,
                error_image=UploadedFile(
                    file=open(omr_file, 'rb')
                ),
                category=OMRNPSError.QR_UNRECOGNIZED,
                page_number=i,
            )
            continue
        
        try:
            _, sequential, object_id  = qr_content.split(':')
            sequential = int(sequential)
            object_id = uuid.UUID(object_id)
        except Exception as e:
            OMRNPSError.objects.create(
                upload=omr_nps_upload,
                error_image=UploadedFile(
                    file=open(omr_file, 'rb')
                ),
                category=OMRNPSError.QR_UNRECOGNIZED,
                page_number=i,
            )
            continue

        sheet_data['page_number'] = i
        sheet_data['sequential'] = sequential
        sheet_data['file_path'] = omr_file
        sheet_data['object_id'] = object_id
        uploads_data.append(sheet_data)
    
    return (nps_upload_id, uploads_data)