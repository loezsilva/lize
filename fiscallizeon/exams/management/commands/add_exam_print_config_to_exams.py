from django.core.management.base import BaseCommand

from fiscallizeon.clients.models import Client, ExamPrintConfig

from ...models import Exam


class Command(BaseCommand):
    help = 'Adiciona configuração de impressão de caderno a todos os cadernos'

    def handle(self, *args, **kwargs):
        for client in Client.objects.all():
            exam_print_config = client.get_exam_print_config()
            for exam in Exam.objects.filter(coordinations__unity__client=client).distinct():
                exam_print_config.pk = None
                exam_print_config.name = f'Configuração {exam.name}'
                exam_print_config.save()

                exam.exam_print_config = exam_print_config
                exam.save()
