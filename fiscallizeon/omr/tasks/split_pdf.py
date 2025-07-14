import os
import glob
import shutil

import requests
from pdf2image import convert_from_path

from django.conf import settings

from fiscallizeon.celery import app
from fiscallizeon.omr.models import OMRUpload
from fiscallizeon.core.storage_backends import PrivateMediaStorage

@app.task
def split_pdf(upload_id):
    omr_upload = OMRUpload.objects.using('default').get(pk=upload_id)

    os.makedirs(os.path.join(settings.OMR_UPLOAD_DIR), exist_ok=True)
    raw_filename = os.path.join(settings.OMR_UPLOAD_DIR, f'{upload_id}.pdf')

    with requests.get(omr_upload.raw_pdf.url, stream=True) as r:
        with open(raw_filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

    os.makedirs(f'tmp/{upload_id}', exist_ok=True)

    convert_from_path(
        f'tmp/{upload_id}.pdf',
        output_folder=f'tmp/{upload_id}/',
        fmt="jpg"
    )

    page_paths = glob.glob(f'tmp/{upload_id}/*.jpg')

    omr_upload.total_pages = len(page_paths)
    omr_upload.save()

    spaces_paths = []

    fs = PrivateMediaStorage()
    for page in page_paths:
        filename = fs.save(
            f"omr/scans/{upload_id}/{page.split('/')[-1]}",
            open(page, 'rb')
        )
        spaces_paths.append(filename)
    
    os.remove(f'tmp/{upload_id}.pdf')
    return (upload_id, spaces_paths)