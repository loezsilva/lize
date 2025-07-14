# coding=utf-8
from django import template
register = template.Library()

@register.filter
def cleaned_params(request):
    return f"?{request.META['QUERY_STRING']}" if request.META['QUERY_STRING'] else ''