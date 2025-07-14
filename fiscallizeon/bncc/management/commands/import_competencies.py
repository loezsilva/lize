import csv

from django.core.management.base import BaseCommand
from django.utils import timezone

from fiscallizeon.subjects.models import KnowledgeArea, Subject
from fiscallizeon.bncc.models import Competence

class Command(BaseCommand):
    help = 'Importa as competências de ensinos fundamental e médio'

    def add_arguments(self, parser):
        parser.add_argument('filename', nargs='+', type=str)
        parser.add_argument('level', nargs='+', type=int)

    def get_component_knowledge_area(self, component):
        knowledge_areas = { 
            'Língua Portuguesa': 'Linguagens',
            'Arte': 'Linguagens',
            'Educação Física': 'Linguagens',
            'Língua Inglesa': 'Linguagens',
            'Matemática': 'Matemática',
            'Ciências': 'Ciências da Natureza',
            'Geografia': 'Ciências Humanas',
            'História': 'Ciências Humanas',
            'Ensino religioso': 'Ensino Religioso',
        }

        return knowledge_areas.get(component, None)

    def handle(self, *args, **kwargs):
        filename = kwargs.get('filename')[0]
        level = kwargs.get('level')[0]

        with open(filename) as csv_file:
            if level == 0:
                knowledge_area = KnowledgeArea.objects.get(
                    name=filename[:-4],
                )

                subject, _ = Subject.objects.get_or_create(
                    knowledge_area=knowledge_area,
                    name='Geral',
                )

            elif level == 1:
                knowledge_area = KnowledgeArea.objects.get(
                    name=self.get_component_knowledge_area(filename[:-4]),
                )

                subject, _ = Subject.objects.get_or_create(
                    knowledge_area=knowledge_area,
                    name=filename[:-4],
                )

            else:
                self.stdout.write(self.style.ERROR('Nível de ensino não existe'))
                exit()

            csv_reader = csv.DictReader(csv_file)

            for row in csv_reader:
                Competence.objects.get_or_create(
                    text=row['name'],
                    subject=subject
                )