import os
import ssl

from celery import Celery
from celery.schedules import crontab

from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fiscallizeon.settings')

app = Celery('fiscallizeon')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

if settings.CELERY_REDIS_SSL_ENABLED:
    app.conf.redis_backend_use_ssl = {       
        'ssl_cert_reqs': ssl.CERT_NONE
    }