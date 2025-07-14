from django import template
from datetime import datetime

register = template.Library()

@register.filter
def format_date_input(value):
    try:
        if value:
            if isinstance(value, str):
                value = datetime.strptime(value, '%Y-%m-%d') or datetime.strptime(value, '%d-%m-%Y')
            value = value.strftime("%Y-%m-%d")
            return value
        return ""
    except Exception as e:
        return ""

register.filter('format_date_input', format_date_input)