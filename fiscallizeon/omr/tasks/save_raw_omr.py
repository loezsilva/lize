from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from fiscallizeon.celery import app
from fiscallizeon.omr.models import OMRUpload


"""
DEPRECATED
"""
@app.task
def save_raw_omr(upload_id):
    if settings.DEBUG:
        return upload_id

    omr_upload = OMRUpload.objects.using('default').get(pk=upload_id)
    omr_upload.raw_pdf = UploadedFile(open(f'tmp/{upload_id}.pdf', 'rb'))
    omr_upload.save()
    return upload_id