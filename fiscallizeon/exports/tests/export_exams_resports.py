from django.test import TestCase
from django.test import Client

from fiscallizeon.applications.models import Application
from fiscallizeon.exams.models import Exam

def export_exams_reports():
    """
    Export exams to CSV and save reponse to file
    """
    c = Client()
    c.login(username='grafica@ph.com.br', password='fiscallize2021')

    exams = Exam.objects.filter(
        coordinations__unity__client__pk='86ba20fe-3822-4f72-ab9a-01720bf93662',
        application__date__gte='2021-09-27',
        application__date__lte='2021-10-08',
    ).distinct()

    for exam in exams:
        response = c.get(f'/exportacao/prova/{exam.pk}/respostas?formato=csv')

        with open(f'fiscallizeon/exports/exams/{exam.name.replace("/", "")}.csv', 'wb') as file:
            file.write(response.content)

