# coding=utf-8
import itertools
from django import template
from django.core.cache import cache

from fiscallizeon.exams.models import ExamQuestion

register = template.Library()

@register.filter
def increment(iterator):
  return next(iterator)

@register.filter
def first_item_iterator(iterator):
  return itertools.count(start=1)

@register.filter
def number_print_question(question, exam):
    return exam.number_print_question(question)

@register.filter
def randomized_number_print_question(question, randomization_version):
  exam = randomization_version.application_student.application.exam
  return exam.number_print_question(question, randomization_version)

@register.filter
def randomized_application_number_print_question(question, application_randomization_version):
  exam = application_randomization_version.application.exam
  return exam.number_print_question(question, application_randomization_version=application_randomization_version)
