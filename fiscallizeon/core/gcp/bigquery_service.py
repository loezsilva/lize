import os
import json
import tempfile

from google.cloud import bigquery
from google.cloud.bigquery import WriteDisposition

from django.conf import settings

from fiscallizeon.core.gcp.utils import _get_service_account_json


def load_from_parquet(remote_path, table_id, append=False):
    # table_id = "your-project.your_dataset.your_table_name 
    account_info = _get_service_account_json()

    tf = tempfile.NamedTemporaryFile()
    tf.write(json.dumps(account_info).encode('utf-8'))
    tf.seek(0)
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = tf.name

    client = bigquery.Client()

    disposition = WriteDisposition.WRITE_APPEND if append else WriteDisposition.WRITE_TRUNCATE
    job_config = bigquery.LoadJobConfig(
        write_disposition=disposition,
        source_format=bigquery.SourceFormat.PARQUET,
    )

    uri = f"gs://{settings.GCP_STORAGE_BUCKET}/{remote_path}"
    load_job = client.load_table_from_uri(
        uri, table_id, job_config=job_config
    )

    load_job.result()

    destination_table = client.get_table(table_id)
    print("Loaded {} rows.".format(destination_table.num_rows))