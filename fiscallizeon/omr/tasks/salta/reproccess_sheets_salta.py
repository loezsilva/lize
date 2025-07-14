import os

from celery import chain

from fiscallizeon.celery import app
from fiscallizeon.omr.tasks.salta.process_omr_errors_salta import process_omr_errors_salta
from fiscallizeon.omr.tasks.salta.handle_answers_salta import handle_answers_salta
from fiscallizeon.omr.tasks.finish_processing import finish_processing


@app.task
def reproccess_sheets_salta(upload_id, omr_error_list):
    RETRY_NUMBER = 1
    chain(
        process_omr_errors_salta.s(upload_id, omr_error_list),
        handle_answers_salta.s(),
        finish_processing.s()
    ).apply_async(task_id=f'REPROCESS_OMR_{upload_id}_{RETRY_NUMBER}')