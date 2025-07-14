# coding=utf-8
from django import template

register = template.Library()

@register.filter
def truncate(value, length=5):
    return value[:length]
