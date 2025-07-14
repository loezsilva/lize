# coding=utf-8
from django import template
from django.db.models import Count

register = template.Library()
@register.filter
def examteachersubject_count(user):
    teacher = user.inspector
    return teacher.get_exams_to_review().annotate(
        count=Count('examquestion'),
    ).filter(
        count__gt=0
    ).count()
