from django import template
from fiscallizeon.exams.models import Exam
from fiscallizeon.subjects.models import Subject
register = template.Library()

@register.filter
def get_exam(pk):
    return Exam.objects.get(pk=pk)

@register.filter
def get_subject(pk):
    return Subject.objects.get(pk=pk)

