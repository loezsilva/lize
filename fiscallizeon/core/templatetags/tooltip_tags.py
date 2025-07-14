from django import template

register = template.Library()

@register.filter
def get_rest_of_list(list, shown_number):
    return list[int(shown_number):]