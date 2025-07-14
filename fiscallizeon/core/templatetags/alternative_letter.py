from django import template

register = template.Library()

@register.filter
def alternative_letter(value):
    if value:
        return {
            1: "A",
            2: "B",
            3: "C",
            4: "D",
            5: "E",
            6: "F"
        }[value]
    else:
        return "A"

register.filter('alternative_letter', alternative_letter)