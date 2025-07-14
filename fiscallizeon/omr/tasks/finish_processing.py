import os
import shutil

from django.conf import settings

from fiscallizeon.celery import app
from fiscallizeon.omr.models import OMRUpload    


@app.task
def finish_processing(upload_id):
    omr_upload = OMRUpload.objects.get(pk=upload_id)
    omr_upload.status = OMRUpload.FINISHED
    omr_upload.save()

    upload_dir = os.path.join(settings.OMR_UPLOAD_DIR, str(upload_id))
    try:
        shutil.rmtree(upload_dir, ignore_errors=True)
    except OSError as e:
        print(e)

    return upload_id
