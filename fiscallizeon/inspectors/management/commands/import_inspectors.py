"""
Colunas necessárias no CSV: 
unidade, nome, email, segmentos, disciplinas
"""

import csv

from django.core.management.base import BaseCommand
from django.db import IntegrityError
from django.db.models import Q

from fiscallizeon.clients.models import Client, Unity, SchoolCoordination
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.classes.models import Grade
from fiscallizeon.subjects.models import Subject


class Command(BaseCommand):
    help = 'Importa professores para todas as coordenações de um cliente'
    TEACHERS_FILE = 'teachers.csv'

    def add_arguments(self, parser):
        parser.add_argument('client_id', nargs=1, type=str)

    def handle(self, *args, **kwargs):
        client = Client.objects.get(pk=kwargs['client_id'][0])
        
        with open(self.TEACHERS_FILE) as csvfile:
            reader = csv.DictReader(csvfile, delimiter=",")
            teachers = list(reader)

        for teacher_csv in teachers:
            try:            
                new_teacher, created = Inspector.objects.update_or_create(
                    email=teacher_csv['email'].strip(),
                    defaults={
                        'name': teacher_csv['nome'].strip(),
                    }
                )
                
                try:
                    unity = Unity.objects.get(name=teacher_csv['unidade'].strip(), client=client)
                except Exception as e:
                    print(teacher_csv['unidade'])

                csv_levels = teacher_csv['segmentos'].split(',')
                levels = [l.strip().upper() for l in csv_levels]

                high_school = 'M' in levels
                elementary_school = 'F' in levels
            
                coordinations = SchoolCoordination.objects.filter(
                    Q(
                        Q(high_school=high_school) |
                        Q(elementary_school=elementary_school)
                    ),
                    unity=unity,
                )

                new_teacher.coordinations.add(*coordinations)

                subjects_csv = teacher_csv['disciplinas'].split(',')
                subjects_list = [s.strip() for s in subjects_csv]

                grade_levels = []
                if high_school:
                    grade_levels.append(Grade.HIGHT_SCHOOL)
                if elementary_school:
                    grade_levels.append(Grade.ELEMENTARY_SCHOOL)
                    grade_levels.append(Grade.ELEMENTARY_SCHOOL_2)


                subjects = Subject.objects.filter(
                    name__in=subjects_list,
                    knowledge_area__grades__level__in=grade_levels,
                ).distinct()


                if len(subjects) < len(subjects_list) * len(levels):
                    raise Exception(f'Disciplina(s) não encontrada(s): {subjects_list}. Nível de ensino: {levels}')

                new_teacher.subjects.add(*subjects)
                print(f'Professor: {new_teacher}. Disciplinas: {subjects.values_list("name")}')

            except IntegrityError as e:
                continue
            except Exception as e:
                import sys, os
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(exc_type, fname, exc_tb.tb_lineno)
                print(e)