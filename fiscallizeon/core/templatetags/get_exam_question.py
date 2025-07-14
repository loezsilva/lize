# coding=utf-8
from django import template
from fiscallizeon.exams.models import ExamQuestion
register = template.Library()

@register.filter
def get_exam_teacher_subject(question, exam):
    if exam_question := ExamQuestion.objects.select_related('exam_teacher_subject').filter(exam_teacher_subject__isnull=False, question=question, exam=exam).first():
        exam_teacher_subject = exam_question.exam_teacher_subject
        return exam_teacher_subject.id if exam_teacher_subject else ""
    else:
        return ""

@register.filter
def get_exam_question(question, exam):
    exam_question = ExamQuestion.objects.filter(question=question, exam=exam).first()
    return exam_question if exam_question else ""