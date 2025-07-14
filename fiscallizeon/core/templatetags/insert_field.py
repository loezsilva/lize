# coding=utf-8
from django import template


register = template.Library()

@register.filter
def insert_field(arg, value):
    if value and arg:
        arg['id'] = str(value)
        
    return arg    