# coding=utf-8
from django import template

from fiscallizeon.answers.models import Attachments, FileAnswer

register = template.Library()

@register.filter
def get_answer_file_link(answer_pk):
    if not answer_pk:
        return None

    answer = FileAnswer.objects.filter(pk=answer_pk).first()
    return answer.arquivo.url if answer and answer.arquivo else ''

@register.filter
def get_answer_attachment_file_link(attachment_pk):
    if not attachment_pk:
        return None
    answer = Attachments.objects.filter(pk=attachment_pk).first()
    return answer.file.url if answer and answer.file else ''