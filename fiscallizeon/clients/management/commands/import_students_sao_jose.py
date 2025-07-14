import csv
import os
import requests
import shutil
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
        client = Client.objects.get(pk="5bbe72b2-7a16-4f8c-969f-554a67719c87")
        path_file = "https://fiscallizeremote.nyc3.cdn.digitaloceanspaces.com/temp/alunos_sao_jose_1-5.csv"

        with requests.get(path_file, stream=True) as r:
            tmp_file = os.path.join("/tmp/saojose2.csv")

            with open(tmp_file, 'wb') as f:
                shutil.copyfileobj(r.raw, f)

            with open(tmp_file, 'r') as file:
                csvreader = csv.DictReader(file)
                start = 14388
                for row in csvreader:
                    unity_name = row["unidade"]
                    school_class_name = row["turma"]
                    quantity = int(row["quantidade"]) + 10
                    unity_code = school_class_name.lower().replace(" ", "-")

                    print(unity_name, school_class_name, quantity)

                    unity, unity_created = Unity.objects.get_or_create(
                        client=client,
                        name=unity_name,
                        unity_type=Unity.SUBSIDIARY
                    )

                    coordination, coordination_created = SchoolCoordination.objects.get_or_create(
                        name=unity_name,
                        responsible_name="Responsável",
                        responsible_email="responsavel@email.com",
                        responsible_phone="11988889999",
                        high_school=True,
                        elementary_school=True,
                        can_see_all=False,
                        can_see_finances=False,
                        defaults={
                            'unity':unity,
                        }
                    )

                    coordination_user = User.objects.filter(
                        username=f'{unity_code}@saojose.com'
                    ).first()

                    if not coordination_user:
                        coordination_user = User.objects.create(
                            username=f'{unity_code}@saojose.com',
                            name=unity_name,
                            email=f'{unity_code}@saojose.com',
                            must_change_password=True,
                            is_active=True
                        )

                    coordination_user.set_password(unity_code)
                    coordination_user.save()

                    CoordinationMember.objects.get_or_create(
                        coordination=coordination,
                        user=coordination_user,
                        is_coordinator=True,
                        is_reviewer=True,
                        is_pedagogic_reviewer=True
                    )

                    print(f'{school_class_name}, {unity_code}')

                    grade = Grade.objects.get(
                        name=school_class_name[0],
                        level__in=[Grade.ELEMENTARY_SCHOOL, Grade.ELEMENTARY_SCHOOL_2]
                    )

                    school_class, school_class_created = SchoolClass.objects.get_or_create(
                        name=school_class_name,
                        grade=grade,
                        coordination=coordination,
                        class_type=SchoolClass.REGULAR,
                        school_year=2023
                    )
                    
                    for number in range(start, start+quantity):
                        student_code = f'000000{number}'[-6:]
                        print(student_code)
                        student, student_created = Student.objects.get_or_create(
                            client=client,
                            name=f'Aluno {student_code}',
                            enrollment_number=student_code,
                            email=f'{student_code}@alunosaojose.com.br'
                        )

                        school_class.students.add(student)
                    
                    start = start + quantity
                    print("---------------------------------------------")
