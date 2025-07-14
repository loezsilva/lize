import hmac
import random
import hashlib

from django import template
from django.conf import settings


register = template.Library()

@register.filter
def tawkto_hash(email):
    if settings.TAWKTO_IS_SECURE:
        hash_hmac = hmac.new(
            key=settings.TAWKTO_API_KEY.encode(), msg=email.encode(), digestmod=hashlib.sha256
        ).hexdigest()

        return hash_hmac
    return ''