from django import template

register = template.Library()

@register.filter
def get_attr(obj, attr):
    if type(obj) == dict:
        return obj.get(attr)
    return getattr(obj, attr)