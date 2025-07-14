import os

from celery import chain

from fiscallizeon.celery import app
from fiscallizeon.omr.tasks.split_pdf import split_pdf
from fiscallizeon.omr.tasks.eleva.crop_omr_area_eleva import crop_omr_area_eleva
from fiscallizeon.omr.tasks.remove_files import remove_files
from fiscallizeon.omr.tasks.save_raw_omr import save_raw_omr
from fiscallizeon.omr.tasks.eleva.create_omr_errors_eleva import create_omr_errors_eleva


"""
Chain para processamento de cartões resposta do simulado eleva
"""
@app.task
def proccess_sheets_eleva(upload_id):
    chain(
        save_raw_omr.s(upload_id),
        split_pdf.s(),
        crop_omr_area_eleva.s(),
        create_omr_errors_eleva.s().set(task_id=f'PROCESS_OMR_{upload_id}'),
        remove_files.s(),
    )()