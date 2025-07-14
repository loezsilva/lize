from django import template


register = template.Library()


@register.filter
def percentage(value, denominator, decimals=2):
    if denominator == 0:
        return '-'

    percent = (value / denominator) * 100

    if percent % 2 == 0:
        return f'{percent:.0f}%'

    return f'{percent:.{decimals}f}%'
