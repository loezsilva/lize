# coding=utf-8
from django import template


register = template.Library()

@register.filter
def proportion(value, denominator):
    if value and denominator > 0:
        value /= denominator
        return value * 100
    return 0