# coding=utf-8
from django import template
from fiscallizeon.core.utils import round_half_up


register = template.Library()

@register.filter
def round_to(value, base=5):
    return base * round_half_up(value/base)
