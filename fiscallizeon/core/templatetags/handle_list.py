from django import template


register = template.Library()


@register.filter
def all_attr_true(items, attr_name):
    return all(getattr(item, attr_name, False) for item in items)
