import random
from django import template

register = template.Library()

@register.filter
def shuffle(arg , condition):
    if condition:
        tmp = list(arg)[:]
        random.shuffle(tmp)
        return tmp
    
    return arg