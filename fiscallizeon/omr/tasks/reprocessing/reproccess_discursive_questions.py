from celery import chain, states, group

from fiscallizeon.celery import app
from fiscallizeon.omr.tasks.discursive.handle_discursive_answers import handle_discursive_answers
from fiscallizeon.omr.tasks.essay.handle_essay_answer import handle_essay_answer
from fiscallizeon.omr.tasks.finish_processing import finish_processing
from fiscallizeon.omr.models import OMRUpload, OMRCategory

@app.task
def error_handle(request, *args, **kwargs):
    RETRY_NUMBER = 1
    omr_upload = OMRUpload.objects.filter(pk=request.kwargs["args"][0])

    if omr_upload:
        omr_upload.update(status=OMRUpload.FINISHED)

        app.backend.store_result(
            task_id=f'REPROCESS_OMR_{omr_upload[0].pk}_{RETRY_NUMBER}',
            result=None,
            state=states.FAILURE,
        )

@app.task
def reproccess_discursive_questions(upload_id, omr_error_list):
    RETRY_NUMBER = 1

    task_list = []
    for error in omr_error_list:
        if error.get('sequential', '') == OMRCategory.ESSAY_1:            
            essay_error = {
                'object_id': error['object_id'],
                'exam_question_pk': error['answers_data'][0]['exam_question_pk'],
                'image_path': error['answers_data'][0]['image_path'],
                'omr_error': error['answers_data'][0]['omr_error'],
            }

            task_list.append(
                handle_essay_answer.s(args=(upload_id, essay_error))
            )
            continue

        task_list.append(
            handle_discursive_answers.s(args=(upload_id, error))
        )
    
    chain(
        group(task_list),
        finish_processing.si(upload_id)
    ).on_error(
        error_handle.s()
    ).apply_async(
        task_id=f'REPROCESS_OMR_{upload_id}_{RETRY_NUMBER}', 
    )