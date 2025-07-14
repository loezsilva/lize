from django import template

register = template.Library()

@register.filter
def escape_single_quotes(value):
    return value.replace("'", "\\'")
