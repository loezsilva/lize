# coding=utf-8
from django import template


register = template.Library()

@register.filter
def insert_last_status(arg, value):
    if arg:
        arg['last_status'] = value
        
    return arg    