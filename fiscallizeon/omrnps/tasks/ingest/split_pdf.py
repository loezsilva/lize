import os
import glob
import shutil

import requests
from pdf2image import convert_from_path

from django.conf import settings

from fiscallizeon.celery import app
from fiscallizeon.omrnps.models import OMRNPSUpload

@app.task
def split_pdf(nps_upload_id):
    omr_nps_upload = OMRNPSUpload.objects.using('default').get(pk=nps_upload_id)
    upload_dir = os.path.join(settings.OMR_UPLOAD_DIR, str(nps_upload_id))

    os.makedirs(settings.OMR_UPLOAD_DIR, exist_ok=True)
    raw_filename = os.path.join(settings.OMR_UPLOAD_DIR, f'{nps_upload_id}.pdf')

    with requests.get(omr_nps_upload.raw_pdf.url, stream=True) as r:
        with open(raw_filename, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

    os.makedirs(upload_dir, exist_ok=True)

    convert_from_path(
        raw_filename, 
        output_folder=upload_dir,
        fmt="jpg"
    )

    page_paths = glob.glob(f'{upload_dir}/*.jpg')

    omr_nps_upload.total_pages = len(page_paths)
    omr_nps_upload.save()

    os.remove(raw_filename)
    return nps_upload_id