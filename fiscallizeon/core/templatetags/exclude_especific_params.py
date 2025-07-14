# coding=utf-8
from django import template

register = template.Library()

@register.filter
def exclude_especific_params(request, excluded_params):
    params = ""
    for value in request.META['QUERY_STRING'].split('&'):
        if not excluded_params.split(',').__contains__(value.split('=')[0]):
            params += "&" + value

    params = params.replace('&&', '&').replace('?&', '?')

    return params