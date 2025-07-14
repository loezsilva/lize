# coding=utf-8
from django import template


register = template.Library()

@register.filter
def insert_key(arg, value):
    if arg:
        arg['objectOrder'] = value
        
    return arg    