from django import template

from fiscallizeon.core.storage_backends import PrivateMediaStorage

register = template.Library()

@register.filter
def s3_url(value):
    storage = PrivateMediaStorage()
    
    try:
       return storage.url(value)
    except IndexError:
        return value