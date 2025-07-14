from django.conf import settings
from django import template

register = template.Library()

@register.filter
def cdn_url(value):
    if settings.AWS_S3_ENDPOINT_URL in value:
        try:
            cdn_domain = 'https://' + settings.AWS_S3_CUSTOM_DOMAIN.split('/')[0]
            return value.replace(settings.AWS_S3_ENDPOINT_URL, cdn_domain)
        except IndexError:
            return value
    else:
        return value