from django.core.management.base import BaseCommand

from fiscallizeon.exams.models import ExamHeader

from fiscallizeon.clients.models import ExamPrintConfig
from django.db.models import Q

class Command(BaseCommand):
    help = 'Seta para false todas as provas que é cópia ou que te o nome configuração cópia no nome da configuração'

    def handle(self, *args, **kwargs):

        configs = ExamPrintConfig.objects.filter(
            Q(name__icontains='Configuração CÓPIA') | 
            Q(exams__source_exam__isnull=False)
        ).distinct()

        configs.update(is_default=False)