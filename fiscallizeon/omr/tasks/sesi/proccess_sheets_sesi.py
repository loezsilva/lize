import os

from celery import chain

from fiscallizeon.celery import app
from fiscallizeon.omr.tasks.split_pdf import split_pdf
from fiscallizeon.omr.tasks.finish_processing import finish_processing
from fiscallizeon.omr.tasks.sesi.handle_enrollments_sesi import handle_enrollments_sesi
from fiscallizeon.omr.tasks.sesi.handle_answers_sesi import handle_answers_sesi


"""
Chain para processamento de cartões resposta do modelo padrão Sesi
"""
@app.task
def proccess_sheets_sesi(upload_id):
    chain(
        split_pdf.s(upload_id),
        handle_enrollments_sesi.s().set(task_id=f'PROCESS_FISCALLIZE_DISCURSIVE_{upload_id}'),
        handle_answers_sesi.s().set(task_id=f'PROCESS_LIZE_SHEETS_{upload_id}'),
        finish_processing.s(),
    )()