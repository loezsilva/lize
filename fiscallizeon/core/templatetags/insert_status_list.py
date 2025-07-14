# coding=utf-8
from django import template


register = template.Library()

@register.filter
def insert_status_list(arg, value):
    if arg:
        arg['status_list'] = value
        
    return arg    