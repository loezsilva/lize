# coding=utf-8
from django import template
register = template.Library()

@register.filter
def call_function_with_params(object, params):
    function_name = params.split(',')[0]
    params = params.split(',')[1:]
    
    return getattr(object, function_name)(*params)


@register.filter
def concat_string(string1, string2):
    
    return f'{string1}{string2}'