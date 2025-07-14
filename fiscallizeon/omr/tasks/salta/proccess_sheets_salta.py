import os

from celery import chain

from fiscallizeon.celery import app
from fiscallizeon.omr.tasks.split_pdf import split_pdf
from fiscallizeon.omr.tasks.finish_processing import finish_processing
from fiscallizeon.omr.tasks.salta.handle_enrollments_salta import handle_enrollments_salta
from fiscallizeon.omr.tasks.salta.handle_answers_salta import handle_answers_salta


"""
Chain para processamento de cartões resposta do modelo padrão Salta
"""
@app.task
def proccess_sheets_salta(upload_id):
    chain(
        split_pdf.s(upload_id),
        handle_enrollments_salta.s().set(task_id=f'PROCESS_FISCALLIZE_DISCURSIVE_{upload_id}'),
        handle_answers_salta.s().set(task_id=f'PROCESS_LIZE_SHEETS_{upload_id}'),
        finish_processing.s(),
    )()