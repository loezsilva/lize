# coding=utf-8
from django import template
from django.db.models import Case, When

from fiscallizeon.exams.models import Question
from fiscallizeon.exams.json_utils import convert_json_to_exam_questions_list

register = template.Library()

@register.filter
def get_await_correction_count(exam_question, applications_student):

    if exam_question.question.category == Question.FILE:
        return applications_student.filter(file_answers__question=exam_question.question, file_answers__teacher_grade__isnull=True).count()
    elif exam_question.question.category == Question.TEXTUAL:
        return applications_student.filter(textual_answers__question=exam_question.question, textual_answers__teacher_grade__isnull=True).count()
    
    return 0

@register.filter
def sort_exam_questions_by_randomization_version(exam_questions, application_randomization_version=None):
    if not application_randomization_version:
        return exam_questions

    exam_questions_json = convert_json_to_exam_questions_list(application_randomization_version.exam_json)
    randomized_exam_question_pks = [q['pk'] for q in exam_questions_json]
    preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(randomized_exam_question_pks)])
    
    if exam_questions:
        return exam_questions.filter(pk__in=randomized_exam_question_pks).order_by(preserved)
    return exam_questions