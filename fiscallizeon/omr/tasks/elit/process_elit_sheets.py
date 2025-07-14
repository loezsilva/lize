from celery import chain, group, states

from fiscallizeon.celery import app
from fiscallizeon.omr.tasks.split_pdf import split_pdf
from fiscallizeon.omr.tasks.finish_processing import finish_processing
from fiscallizeon.omr.tasks.elit.crop_answer_area import crop_answer_area
from fiscallizeon.omr.tasks.elit.read_answers import read_answers
from fiscallizeon.omr.tasks.elit.handle_answers import handle_answers


@app.task
def error_handle(request, *args, **kwargs):
    app.backend.store_result(
        task_id=f'PROCESS_LIZE_SHEETS_{request.args[0]}',
        result=None,
        state=states.FAILURE,
    )


@app.task
def process_elit_sheets(upload_id):
    chain(
        split_pdf.s(upload_id),
        crop_answer_area.s(),
        read_answers.s(),
        handle_answers.s().set(task_id=f'PROCESS_LIZE_SHEETS_{upload_id}'),
        finish_processing.si(upload_id),
    ).on_error(
        error_handle.s()
    )()