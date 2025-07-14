from celery import chain, chord, states

from fiscallizeon.celery import app
from fiscallizeon.omr.models import OMRCategory, OMRUpload
from fiscallizeon.omr.tasks.split_pdf import split_pdf
from fiscallizeon.omr.tasks.read_sheets_directory_fiscallize import read_sheets_directory_fiscallize
from fiscallizeon.omr.tasks.handle_answers import handle_answers
from fiscallizeon.omr.tasks.finish_processing import finish_processing
from fiscallizeon.omr.tasks.correct_discursives import correct_discursives
from fiscallizeon.omr.tasks.read_files_qr import read_files_qr
from fiscallizeon.omr.tasks.handle_avulse_sheets import handle_avulse_sheets
from fiscallizeon.omr.tasks.discursive.crop_answer_area import crop_answer_area
from fiscallizeon.omr.tasks.discursive.handle_discursive_answers import handle_discursive_answers
from fiscallizeon.omr.tasks.essay.read_essay_sheet import read_essay_sheet
from fiscallizeon.omr.tasks.essay.handle_essay_answer import handle_essay_answer


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

    objective_omr_categories = [
        OMRCategory.FISCALLIZE, 
        OMRCategory.ENEM, 
        OMRCategory.HYBRID_025, 
        OMRCategory.SUM_1, 
        OMRCategory.OFFSET_1,
        OMRCategory.SUBJECTS_1,
        OMRCategory.REDUCED_MODEL,
    ]
    discursive_omr_categories = [
        OMRCategory.DISCURSIVE_025,
    ]
    essay_omr_categories = [
        OMRCategory.ESSAY_1,
    ]

    auto_correct_discursives = False
    if client := omr_upload.user.get_clients().first():
        auto_correct_discursives = client.has_discursive_auto_correction

    task_list = []
    for page in uploads_data:
        if page['operation_type'] not in ['S', 'R']:
            continue

        if page['sequential'] in objective_omr_categories:
            task_list.append(
                chain(
                    read_sheets_directory_fiscallize.s(upload_id, page),
                    handle_answers.s(),
                )
            )
            continue

        if page['sequential'] in discursive_omr_categories:
            page['auto_correct_discursives'] = auto_correct_discursives
            task_list.append(
                chain(
                    crop_answer_area.s(upload_id, page),
                    handle_discursive_answers.s(),
                )
            )
            continue

        if page['sequential'] in essay_omr_categories:
            task_list.append(
                chain(
                    read_essay_sheet.s(upload_id, page),
                    handle_essay_answer.s(),
                )
            )
    
    chord(
        task_list,
    )(
        chain(
            finish_processing.si(upload_id),
            correct_discursives.s()
        )
    )

    return args

@app.task
def proccess_sheets(upload_id):
    chain(
        split_pdf.s(upload_id),
        read_files_qr.s(),
        handle_avulse_sheets.s(),
        read_sheets.s(),
    ).set(
        task_id=f'PROCESS_LIZE_SHEETS_{upload_id}'
    ).on_error(
        error_handle.s()
    )()