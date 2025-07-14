import os

from celery import chain

from fiscallizeon.celery import app
from fiscallizeon.omr.tasks.split_pdf import split_pdf
from fiscallizeon.omr.tasks.olimpiada_rio.crop_omr_area_rio import crop_omr_area_rio
from fiscallizeon.omr.tasks.remove_files import remove_files
from fiscallizeon.omr.tasks.save_raw_omr import save_raw_omr
from fiscallizeon.omr.tasks.olimpiada_rio.create_omr_errors_rio import create_omr_errors_rio


"""
Chain para processamento de cartões resposta do município do rio. Fluxo temporário que poderá ser reaproveitado no futuro
"""
@app.task
def proccess_sheets_rio(upload_id):
    chain(
        save_raw_omr.s(upload_id),
        split_pdf.s(),
        crop_omr_area_rio.s(),
        create_omr_errors_rio.s().set(task_id=f'PROCESS_OMR_{upload_id}'),
        remove_files.s(),
    )()