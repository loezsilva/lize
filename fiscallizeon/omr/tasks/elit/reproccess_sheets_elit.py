import os

from celery import chain

from fiscallizeon.celery import app
from fiscallizeon.omr.tasks.elit.process_omr_errors_elit import process_omr_errors_elit
from fiscallizeon.omr.tasks.elit.read_answers import read_answers
from fiscallizeon.omr.tasks.elit.handle_answers import handle_answers
from fiscallizeon.omr.tasks.finish_processing import finish_processing


@app.task
def reproccess_sheets_elit(upload_id, omr_error_list):
    RETRY_NUMBER = 1
    chain(
        process_omr_errors_elit.s(upload_id, omr_error_list),
        read_answers.s(),
        handle_answers.s(),
        finish_processing.s()
    ).apply_async(task_id=f'REPROCESS_OMR_{upload_id}_{RETRY_NUMBER}')