from celery import chain, chord, states

from fiscallizeon.celery import app
from fiscallizeon.omr.models import OMRUpload
from fiscallizeon.omr.tasks.split_pdf import split_pdf
from fiscallizeon.omr.tasks.handle_answers import handle_answers
from fiscallizeon.omr.tasks.offset_schoolclass.read_sheets import read_sheets as read_offset_schoolclass_sheets
from fiscallizeon.omr.tasks.finish_processing import finish_processing


@app.task
def error_handle(request, *args, **kwargs):
    app.backend.store_result(
        task_id=f'PROCESS_LIZE_SHEETS_{request.args[0]}',
        result=None,
        state=states.FAILURE,
    )

@app.task
def read_sheets(args):
    upload_id, uploads_data = args

    omr_upload = OMRUpload.objects.using('default').get(pk=upload_id)
    students_class_count = omr_upload.school_class.students.count()

    task_list = []
    for index, page in enumerate(uploads_data, 1):
        task_list.append(
            chain(
                read_offset_schoolclass_sheets.s(upload_id, page, index, students_class_count),
                handle_answers.s(),
            )
        )
    
    chord(
        task_list,
    )(
        chain(
            finish_processing.si(upload_id),
        )
    )

    return args

@app.task
def proccess_sheets_offset(upload_id):
    chain(
        split_pdf.s(upload_id),
        read_sheets.s(),
    ).set(
        task_id=f'PROCESS_LIZE_SHEETS_{upload_id}'
    ).on_error(
        error_handle.s()
    )()