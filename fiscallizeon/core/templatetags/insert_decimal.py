# coding=utf-8
from django import template


register = template.Library()

@register.filter
def insert_decimal(arg, value):
    if arg:
        arg['weight'] = value
        
    return arg