import csv

from django.core.management.base import BaseCommand
from django.utils import timezone

from fiscallizeon.bncc.models import Abiliity, ActingField
from fiscallizeon.subjects.models import Subject, KnowledgeArea

class Command(BaseCommand):
    help = 'Importa as habilidades do ensino médio'

    def add_arguments(self, parser):
        parser.add_argument('filename', nargs='+', type=str)

    def handle(self, *args, **kwargs):
        filename = kwargs.get('filename')[0]

        with open(filename) as csv_file:
            knowledge_area = KnowledgeArea.objects.get(
                name=filename[:-4],
            )

            csv_reader = csv.DictReader(csv_file)

            for row in csv_reader:
                subject, _ = Subject.objects.get_or_create(
                    knowledge_area=knowledge_area,
                    name='Geral'
                )

                ability, _ = Abiliity.objects.get_or_create(
                    code=row['codigo'],
                    text=row['description'],
                    subject=subject,
                )

                if row.get('acting_field', None):
                    acting_field, _ = ActingField.objects.get_or_create(text=row['acting_field'])
                    ability.acting_field = acting_field
                    ability.save()

                for grade in knowledge_area.grades.all():
                    ability.grades.add(grade)

                