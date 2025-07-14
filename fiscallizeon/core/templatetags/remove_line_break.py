from django import template

register = template.Library()

@register.filter
def remove_line_break(value):
    if value:
        return value.replace("\n","\\n").replace("\r", '\\r')
    else:
        return value

register.filter('remove_line_break', remove_line_break)