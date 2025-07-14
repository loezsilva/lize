import os
import shutil

from django.conf import settings

from fiscallizeon.celery import app
from fiscallizeon.omrnps.models import OMRNPSUpload


@app.task
def finish_processing(omr_nps_upload_id):
    OMRNPSUpload.objects.filter(pk=omr_nps_upload_id).update(status=OMRNPSUpload.FINISHED)

    upload_dir = os.path.join(settings.OMR_UPLOAD_DIR, str(omr_nps_upload_id))
    try:
        pass
        # shutil.rmtree(upload_dir)
    except OSError as e:
        print(f"Erro ao excluir os arquivos do upload: {e}")
