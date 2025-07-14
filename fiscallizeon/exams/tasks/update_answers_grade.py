from celery.exceptions import Ignore
from django.db.models import F, Value
from django.apps import apps

from fiscallizeon.celery import app
from fiscallizeon.answers.models import FileAnswer, TextualAnswer

@app.task()
def update_answers_grade(exam_question_pk, proportion):
    try:
        ExamQuestion = apps.get_model("exams", "ExamQuestion")
        exam_question = ExamQuestion.objects.using('default').get(pk=exam_question_pk)
        t = FileAnswer.objects.filter(
            teacher_grade__gt=0,
            question=exam_question.question,
            student_application__application__exam=exam_question.exam,
        ).distinct().update(
            teacher_grade=F('teacher_grade')*Value(proportion)
        )

        t = TextualAnswer.objects.filter(
            teacher_grade__gt=0,
            question=exam_question.question,
            student_application__application__exam=exam_question.exam,
        ).distinct().update(
            teacher_grade=F('teacher_grade')*Value(proportion)
        )
    except Exception as e:
        print(e)
        raise Ignore()