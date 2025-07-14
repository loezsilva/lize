# coding=utf-8
from django import template
from fiscallizeon.core.utils import percentage_value
from fiscallizeon.core.utils import round_half_up


register = template.Library()
@register.filter
def sub(n1, n2):
    return n1 - n2


@register.filter()
def get_loop_middle(n1):
    middle = round(n1 / 2)
    return middle
    
@register.filter
def divide(value, arg):
    if value and arg:
        try:
            return int(value) / int(arg)
        except (ValueError, ZeroDivisionError):
            return None
    return None
    
@register.filter
def multiply(value, multiple):
    try:
        return value * multiple
    except Exception as e:
        return None

@register.filter()
def performance_percentage(value):
    if value:
        return percentage_value(value)
    else:
        return 0
