import os

from celery import chain

from fiscallizeon.celery import app
from fiscallizeon.omrnps.tasks.ingest.reprocess.process_data_without_qr import process_data_without_qr
from fiscallizeon.omrnps.tasks.ingest.read_sheets_directory import read_sheets_directory
from fiscallizeon.omrnps.tasks.ingest.finish_processing import finish_processing


@app.task
def reproccess_sheets(upload_id, omr_error_list):
    chain(
        process_data_without_qr.s(upload_id, omr_error_list),
        read_sheets_directory.s(),
        finish_processing.si(upload_id),
    ).apply_async(task_id=f'REPROCESS_NPSOMR_{upload_id}')