# coding=utf-8
from django import template
from fiscallizeon.core.utils import round_half_up

register = template.Library()
@register.filter
def separated_distributions(query, arg = 'initial'):
    middle = round(len(query) / 2)
    if arg == 'initial':
        if not len(query) % 2 == 0:
            middle = middle + 1
        return query[:middle]
    else:
        if not len(query) % 2 == 0:
            middle = middle + 1
        return query[middle:]