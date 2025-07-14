from celery import chain, group, states

from fiscallizeon.celery import app
from fiscallizeon.omrnps.tasks.ingest.split_pdf import split_pdf
from fiscallizeon.omrnps.tasks.ingest.read_files_qr import read_files_qr
from fiscallizeon.omrnps.tasks.ingest.read_sheets_directory import read_sheets_directory
from fiscallizeon.omrnps.tasks.ingest.finish_processing import finish_processing


@app.task
def error_handle(request, *args, **kwargs):
    app.backend.store_result(
        task_id=f'PROCESS_NPS_ANSWERS_{request.args[0]}',
        result=None,
        state=states.FAILURE,
    )

@app.task
def proccess_sheets(nps_upload_id):
    chain(
        split_pdf.s(nps_upload_id),
        read_files_qr.s(),
        read_sheets_directory.s().set(task_id=f'PROCESS_NPS_ANSWERS_{nps_upload_id}'),
        finish_processing.s(),
    ).on_error(
        error_handle.s()
    )()