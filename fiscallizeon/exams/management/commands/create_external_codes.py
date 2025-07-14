from datetime import datetime

from django.core.management.base import BaseCommand

from fiscallizeon.exams.models import Exam
from fiscallizeon.clients.models import Client


class Command(BaseCommand):
    help = 'Cria o código único para as provas de um cliente'

    def add_arguments(self, parser):
        parser.add_argument('client_id', nargs='+', type=str)

    def handle(self, *args, **kwargs):
        client_id = kwargs.get('client_id')[0]
        client = Client.objects.get(pk=client_id)

        exams = Exam.objects.filter(
            coordinations__unity__client=client,
            created_at__year=datetime.now().year,
            external_code__isnull=True,
        ).distinct()

        for exam in exams:
            Exam.objects.generate_external_code(exam, client)
            print(f"Código gerado para prova {exam.name}")