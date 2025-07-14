import os

from celery import chain

from fiscallizeon.celery import app
from fiscallizeon.omr.tasks.sesi.process_omr_errors_sesi import process_omr_errors_sesi
from fiscallizeon.omr.tasks.sesi.handle_answers_sesi import handle_answers_sesi
from fiscallizeon.omr.tasks.finish_processing import finish_processing


@app.task
def reproccess_sheets_sesi(upload_id, omr_error_list):
    RETRY_NUMBER = 1
    chain(
        process_omr_errors_sesi.s(upload_id, omr_error_list),
        handle_answers_sesi.s(),
        finish_processing.s()
    ).apply_async(task_id=f'REPROCESS_OMR_{upload_id}_{RETRY_NUMBER}')