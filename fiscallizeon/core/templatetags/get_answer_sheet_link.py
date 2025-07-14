# coding=utf-8
from django import template

from fiscallizeon.applications.models import Application

register = template.Library()

@register.filter
def get_answer_sheet_link(application):
    if not application:
        return None
    
    return application.answer_sheet.url if application.answer_sheet else ''