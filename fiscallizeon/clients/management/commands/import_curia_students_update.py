import csv
import os
import requests
import shutil
import random
from datetime import datetime
from django.db import transaction
from django.core.management.base import BaseCommand

from fiscallizeon.clients.models import Unity, SchoolCoordination, CoordinationMember, Client
from fiscallizeon.accounts.models import User
from fiscallizeon.classes.models import SchoolClass, Grade
from fiscallizeon.students.models import Student

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--path_file', nargs=1, type=str)

    def handle(self, *args, **kwargs):
        client = Client.objects.get(pk="5bbe72b2-7a16-4f8c-969f-554a67719c87") #ID do curiar
        path_file = kwargs['path_file'][0]

        with requests.get(path_file, stream=True) as r:
            tmp_file = os.path.join("/tmp/curiar.csv")
            print("baixou o arquivo")

            with open(tmp_file, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
            # print("copiou")
            # with open('tmp/final_ribamar.csv', 'r') as file:

            with open(tmp_file, 'r') as file:
                csvreader = csv.DictReader(file)
                for index, row in enumerate(csvreader):
                    print(index)
                    student_name = row["aluno"].upper().replace("  ", " ")
                    school_name = row["escola"].upper().replace("  ", " ")
                    class_name = row["turma"].upper().replace("  ", " ")
                    shift_name = row["turno"].upper().replace("  ", " ")
                    date = row["nascimento"].upper().replace("  ", " ")
                    student_enrolment = row["id"].upper().replace("  ", " ")

                    if not shift_name in class_name:
                        class_name = f'{class_name} {shift_name}'

                    unity, created = Unity.objects.get_or_create(
                        client=client,
                        name=school_name
                    )

                    if not unity:
                        print('@@@ sem escol', school_name)
                        continue    

                    coordination = unity.coordinations.all().first()

                    if not coordination:
                        print("@@@ sem coord - ", school_name)
                        coordination =  SchoolCoordination.objects.create(
                            unity=unity,
                            name=school_name,
                            responsible_name="Responsável",
                            responsible_email="responsavel@email.com",
                            responsible_phone="11988889999",
                            high_school=True,
                            elementary_school=True,
                            can_see_all=False,
                            can_see_finances=False,
                        )
                    
                    grade = Grade.objects.get(
                        name=class_name[0],
                        level__in=[Grade.ELEMENTARY_SCHOOL, Grade.ELEMENTARY_SCHOOL_2]
                    )
                    

                    school_class, school_class_created = SchoolClass.objects.get_or_create(
                        grade=grade,
                        name=class_name,
                        school_year=2023,
                        coordination=coordination,
                        class_type=SchoolClass.REGULAR
                    )

                    try:
                        enrollment_number = f'{date.replace("/", "")}-{student_enrolment}'

                        students = Student.objects.filter(
                            name=student_name,
                            client=coordination.unity.client
                        )

                        if not students.count() == 1:
                            students = Student.objects.filter(
                                enrollment_number=enrollment_number,
                                client=coordination.unity.client
                            )

                            if not students.count() == 1:
                                students = Student.objects.filter(
                                    name=student_name,
                                    client=coordination.unity.client,
                                    enrollment_number=enrollment_number,
                                )
                                if not students.count() == 1:
                                    print("mais de 1")
                                    continue
                                else:
                                    student = students.first()
                            else:
                                student = students.first()
                        else:
                            student = students.first()

                        if not student:
                            student, student_created = Student.objects.get_or_create(
                                name=student_name,
                                client=coordination.unity.client,
                                defaults={
                                    "enrollment_number": enrollment_number,
                                    "email": f'{enrollment_number}@projetocuriar.com.br'
                                }
                            )

                        for c in student.classes.all():
                            c.students.remove(student)
                            c.save(skip_hooks=True)

                        school_class.students.add(student)

                        # print("#### FOI")
                    except Exception as e:
                        print("@@@@@@@@@@@@@@@@@@@@" ,e)
