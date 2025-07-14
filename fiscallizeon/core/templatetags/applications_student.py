# coding=utf-8
from django import template


register = template.Library()

@register.filter
def get_performance_bncc(application_student, bncc):
    return application_student.get_performance(application_student, bncc)

@register.filter
def get_performance_recalculate(application_student):
    return application_student.get_performance(recalculate=True)