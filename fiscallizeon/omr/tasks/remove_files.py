import os
import shutil

from django.conf import settings

from fiscallizeon.celery import app

@app.task
def remove_files(upload_id):
    upload_dir = os.path.join(settings.OMR_UPLOAD_DIR, str(upload_id))
    try:
        shutil.rmtree(upload_dir, ignore_errors=True)
    except OSError as e:
        print(e)
