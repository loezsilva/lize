import csv
import re

from django.core.management.base import BaseCommand
from django.utils import timezone

from fiscallizeon.bncc.models import Abiliity, KnowledgeObject, ThematicUnit, LanguagePractice, ActingField, Axis
from fiscallizeon.subjects.models import Subject, KnowledgeArea
from fiscallizeon.classes.models import Grade

class Command(BaseCommand):
    help = 'Importa os subjects (componentes) do ensino fundamental'

    def add_arguments(self, parser):
        parser.add_argument('filename', nargs='+', type=str)

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
        
        with open(filename) as csv_file:
            knowledge_area = KnowledgeArea.objects.get(
                name=self.get_component_knowledge_area(filename[:-4]),
            )

            csv_reader = csv.DictReader(csv_file)

            for row in csv_reader:
                subject, _ = Subject.objects.get_or_create(
                    knowledge_area=knowledge_area,
                    name=filename[:-4]
                )

                ability_code = re.sub(r'\W+', '', row['ability'].split(' ', 1)[0])
                ability_text = row['ability'].split(' ', 1)[1]

                ability, _ = Abiliity.objects.get_or_create(
                    code=ability_code,
                    text=ability_text,
                    subject=subject,
                )

                if row.get('acting_field', None):
                    acting_field, _ = ActingField.objects.get_or_create(text=row['acting_field'])
                    ability.acting_field = acting_field

                if row.get('knowledge_object', None):
                    knowledge_object, _ = KnowledgeObject.objects.get_or_create(text=row['knowledge_object'])
                    ability.knowledge_object = knowledge_object

                if row.get('thematic_unit', None):
                    thematic_unit, _ = ThematicUnit.objects.get_or_create(text=row['thematic_unit'])
                    ability.thematic_unit = thematic_unit

                if row.get('language_practice', None):
                    language_practice, _ = LanguagePractice.objects.get_or_create(text=row['language_practice'])
                    ability.language_practice = language_practice

                if row.get('axis', None):
                    axis, _ = Axis.objects.get_or_create(text=row['axis'])
                    ability.axis = axis

                ability.save()

                for grade in row['grade'].replace(';', ',').split(','):
                    db_grade = Grade.objects.get(
                        name=re.sub(r'[^0-9]', '', grade),
                        level__in=[Grade.ELEMENTARY_SCHOOL, Grade.ELEMENTARY_SCHOOL_2]
                    )
                    ability.grades.add(db_grade)

                