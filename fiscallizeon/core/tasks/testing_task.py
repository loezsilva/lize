from random import random
from datetime import datetime

from fiscallizeon.celery import app
from fiscallizeon.clients.models import Client

from django.template.loader import get_template
from fiscallizeon.core.threadings.sendemail import EmailThread


@app.task
def test_task():
    print(f'######## DATETIME: {datetime.now()}')
    

@app.task
def test_task_repeat():
    now = datetime.now()
    random_number = random()
    client = Client.objects.order_by('?').first()

    template = get_template('mail_template/teste.html')
    html = template.render({"now":now, "random_number":random_number, "client":client})
    subject = 'Teste de envio de email'
    to = ['franklindias99@gmail.com']
    EmailThread(subject, html, to).start()

    

