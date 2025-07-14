from django.core.management.base import BaseCommand
from fiscallizeon.classes.models import Grade
from fiscallizeon.subjects.models import KnowledgeArea

class Command(BaseCommand):
    help = 'Ajusta respostas duplicadas de alunos em optionaswer'

    def handle(self, *args, **kwargs):

        grades = [
            {'name': '1', 'level': Grade.ELEMENTARY_SCHOOL},
            {'name': '2', 'level': Grade.ELEMENTARY_SCHOOL},
            {'name': '3', 'level': Grade.ELEMENTARY_SCHOOL},
            {'name': '4', 'level': Grade.ELEMENTARY_SCHOOL},
            {'name': '5', 'level': Grade.ELEMENTARY_SCHOOL},
            {'name': '6', 'level': Grade.ELEMENTARY_SCHOOL_2},
            {'name': '7', 'level': Grade.ELEMENTARY_SCHOOL_2},
            {'name': '8', 'level': Grade.ELEMENTARY_SCHOOL_2},
            {'name': '9', 'level': Grade.ELEMENTARY_SCHOOL_2},
            {'name': '1', 'level': Grade.HIGHT_SCHOOL},
            {'name': '2', 'level': Grade.HIGHT_SCHOOL},
            {'name': '3', 'level': Grade.HIGHT_SCHOOL},
        ]

        for grade in grades:
            Grade.objects.get_or_create(
                name=grade['name'],
                level=grade['level']
            )

        knowledge_areas = [
            {'name': 'Ciências da Natureza e suas Tecnologias', 'grades': '1,2,3', 'level': Grade.HIGHT_SCHOOL},
            {'name': 'Ciências Humanas e Sociais Aplicadas', 'grades': '1,2,3', 'level': Grade.HIGHT_SCHOOL},
            {'name': 'Linguagens e suas Tecnologias', 'grades': '1,2,3', 'level': Grade.HIGHT_SCHOOL},
            {'name': 'Matemática e suas Tecnologias', 'grades': '1,2,3', 'level': Grade.HIGHT_SCHOOL},

            {'name': 'Linguagens', 'grades': '1,2,3,4,5', 'level': Grade.ELEMENTARY_SCHOOL},
            {'name': 'Matemática', 'grades': '1,2,3,4,5', 'level': Grade.ELEMENTARY_SCHOOL},
            {'name': 'Ciências da Natureza', 'grades': '1,2,3,4,5', 'level': Grade.ELEMENTARY_SCHOOL},
            {'name': 'Ciências Humanas', 'grades': '1,2,3,4,5', 'level': Grade.ELEMENTARY_SCHOOL},
            {'name': 'Ensino Religioso', 'grades': '1,2,3,4,5', 'level': Grade.ELEMENTARY_SCHOOL},

            {'name': 'Linguagens', 'grades': '6,7,8,9', 'level': Grade.ELEMENTARY_SCHOOL_2},
            {'name': 'Matemática', 'grades': '6,7,8,9', 'level': Grade.ELEMENTARY_SCHOOL_2},
            {'name': 'Ciências da Natureza', 'grades': '6,7,8,9', 'level': Grade.ELEMENTARY_SCHOOL_2},
            {'name': 'Ciências Humanas', 'grades': '6,7,8,9', 'level': Grade.ELEMENTARY_SCHOOL_2},
            {'name': 'Ensino Religioso', 'grades': '6,7,8,9', 'level': Grade.ELEMENTARY_SCHOOL_2},
        ]

        all_grades = list(Grade.objects.all().values('id', 'name', 'level'))

        for knowledge_area in knowledge_areas:
            db_knowledge_area, created = KnowledgeArea.objects.get_or_create(
                name=knowledge_area['name']
            )
            for grade_name in knowledge_area['grades'].split(','):
                grade = list(filter(lambda x: x['name'] == grade_name and x['level'] == knowledge_area['level'], all_grades))[0]
                db_knowledge_area.grades.add(grade['id'])
