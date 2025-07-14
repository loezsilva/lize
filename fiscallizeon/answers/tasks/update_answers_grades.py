from fiscallizeon.celery import app
from django.apps import apps

@app.task
def update_sum_answers_grades(question_id):
    SumAnswer = apps.get_model('answers', 'SumAnswer')

    answers = SumAnswer.objects.filter(
        question=question_id
    )

    for sum_answer in answers:
        sum_answer.grade = sum_answer.get_grade_proportion()
        sum_answer.save()