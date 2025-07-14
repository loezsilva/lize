import random
from django import template

register = template.Library()

@register.filter
def remove_double_backslash(arg):
    return arg.replace('\\\\', '\\')