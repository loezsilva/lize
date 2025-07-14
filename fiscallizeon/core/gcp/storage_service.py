import os
import json
import tempfile

from google.cloud import storage

from django.conf import settings

from fiscallizeon.core.gcp.utils import _get_service_account_json


def upload_file(local_path, remote_path):
    account_info = _get_service_account_json()

    tf = tempfile.NamedTemporaryFile()
    tf.write(json.dumps(account_info).encode('utf-8'))
    tf.seek(0)
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = tf.name

    storage_client = storage.Client()
    # buckets = list(storage_client.list_buckets())

    bucket = storage_client.get_bucket(settings.GCP_STORAGE_BUCKET)
    blob = bucket.blob(remote_path)
    blob.upload_from_filename(local_path)
