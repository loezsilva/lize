import re
import csv

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count
from django.db.utils import IntegrityError

from fiscallizeon.students.models import Student
from fiscallizeon.classes.models import SchoolClass, Grade
from fiscallizeon.clients.models import Client, SchoolCoordination, Unity

class Command(BaseCommand):
    help = 'Importa alunos de CSV para o lato sensu'

    STUDENTS_FILE = 'students.csv'
    LATO_PK = 'f1a6a4e9-7b95-4045-b6dd-f720a17a14e1'

    def handle(self, *args, **kwargs):
        try:    
            client = Client.objects.get(pk=self.LATO_PK)

            with open(self.STUDENTS_FILE) as csvfile:
                reader = csv.DictReader(csvfile, delimiter=",")
                students = list(reader)

            for student in students:
                try:
                    unity, _ = Unity.objects.get_or_create(
                        client=client,
                        name=student['unidade'].split(' - ')[2].strip(),
                        unity_type=Unity.SUBSIDIARY,
                    )

                    level = 1 if student['turma'][0] == '1' else 0
                    grade_name = student['turma'][2]

                    coordination, _ = SchoolCoordination.objects.get_or_create(
                        unity=unity,
                        name='Coordenação' + (' fundamental' if level == 1 else ' médio'),
                        responsible_name='Responsável coordenação',
                        responsible_email='responsavel_coord@latosensu.com.br',
                        responsible_phone='92 9999-9999',
                        high_school=level == 0,
                        elementary_school=level == 1,
                    )

                    grade = Grade.objects.get(
                        name=grade_name,
                        level=level,
                    )

                    school_class, _ = SchoolClass.objects.get_or_create(
                        grade=grade,
                        name=student['turma'].strip(),
                        coordination=coordination,
                    )

                    matricula = student['matricula'].strip()

                    new_student, created = Student.objects.update_or_create(
                        client=client,           
                        email=f'{matricula}@latosensu.com.br',
                        defaults={
                            'name': student['nome'].strip(),
                            'enrollment_number': matricula,
                        }
                    )

                    message = 'Criando' if created else 'Atualizando'
                    print(f'{message} aluno {new_student.name}')
                except IntegrityError as e:
                    print(f'Integrity error {student["nome"]}')
                    continue
                
                if new_student in school_class.students.all():
                    continue
                
                school_class.students.add(new_student)

        except Exception as e:
            import sys, os
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            print(e)
            