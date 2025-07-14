import json

from django.conf import settings

from fiscallizeon.celery import app
from fiscallizeon.accounts.models import User
from fiscallizeon.omr.models import OMRUpload
from fiscallizeon.answers.models import FileAnswer
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.ai.openai.questions import handle_textual_answer

@app.task
def correct_application_student_file_answers(application_student_id, user_id):
    print(f"Corrigindo discursivas do application student {application_student_id}")
    user = User.objects.get(pk=user_id)
    file_answers = FileAnswer.objects.filter(
        student_application=application_student_id,
        question__commented_awnser__isnull=False,
    ).exclude(
        question__commented_awnser=''
    ).select_related('question')

    for file_answer in file_answers:
        if not file_answer.question.commented_awnser:
            continue

        raw_response = handle_textual_answer(
            enunciation=file_answer.question.enunciation,
            commented_answer=file_answer.question.commented_awnser,
            student_answer=None,
            question_file=file_answer.arquivo.url,
            user=user,
        )

        try:
            response = json.loads(raw_response)
            file_answer.ai_grade = response.get('percentage', None)
            file_answer.ai_teacher_feedback = response.get('comment', None)
            file_answer.ai_student_feedback = response.get('feedback', None)
            file_answer.save()

            if settings.DEBUG:
                print(f"GPT RESPONSE: {response}")
        except Exception as e:
            print(f'Erro ao tratar retorno da correção do GPT: {raw_response}')
            print(e)

@app.task
def correct_discursives(upload_id):
    print(f"Iniciando correção de discursivas do upload {upload_id}")
    omr_upload = OMRUpload.objects.get(pk=upload_id)

    if not omr_upload.user.client_has_discursive_ai_correction:
        return

    application_students = ApplicationStudent.objects.filter(
        omrstudents__upload=omr_upload,
        application__exam__enable_discursive_ai_correction=True,
    )

    application_students.update(
        is_omr=True,
    )

    for application_student in application_students:
        correct_application_student_file_answers.apply_async(
            args=(application_student.pk, omr_upload.user_id)
        )
