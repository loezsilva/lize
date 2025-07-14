# coding=utf-8
from django import template


register = template.Library()

@register.filter
def adjust_time(arg, value):
    if value and arg:
        return  arg + value
        
    return arg    