from django.core.management.base import BaseCommand

from fiscallizeon.exams.models import ExamHeader

from ...models import Client, ExamPrintConfig


class Command(BaseCommand):
    help = 'Re-cria configuração de impressão padrão dos caderno para todos os cadernos'

    def handle(self, *args, **kwargs):
        ExamPrintConfig.objects.all().delete()
        for client in Client.objects.all():
            exam_header = None
            try:
                exam_header = ExamHeader.objects.filter(
                    user__coordination_member__coordination__unity__client=client,
                    main_header=True,
                ).distinct().first()
            except ExamHeader.DoesNotExist:
                pass

            ExamPrintConfig.objects.create(header=exam_header, client=client)
