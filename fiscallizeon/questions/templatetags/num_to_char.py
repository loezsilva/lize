from django import template

register = template.Library()

@register.filter
def num_to_char(value):
    return chr(64+value)
