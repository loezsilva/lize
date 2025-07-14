import os

from celery import chain

from fiscallizeon.celery import app
from fiscallizeon.omr.tasks.reprocessing.process_data_without_qr import process_data_without_qr
from fiscallizeon.omr.tasks.proccess_sheets import read_sheets

@app.task
def reproccess_sheets(upload_id, omr_error_list):
    RETRY_NUMBER = 1
    chain(
        process_data_without_qr.s(upload_id, omr_error_list),
        read_sheets.s()
    ).apply_async(task_id=f'REPROCESS_OMR_{upload_id}_{RETRY_NUMBER}')