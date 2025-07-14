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
        client = Client.objects.get(pk="b1402156-9533-43a5-9bf5-2eaafd2cfe2c")
        path_file = kwargs['path_file'][0]

        with requests.get(path_file, stream=True) as r:
            tmp_file = os.path.join("/tmp/rio.csv")
            print("baixou o arquivo")

            with open(tmp_file, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
                print("copiou")

            with open(tmp_file, 'r') as file:
                csvreader = csv.DictReader(file)
                with transaction.atomic():
                    for row in csvreader:
                        unity_code = row["DESIGNACAO_NUM"]
                        code_school = row["CD_ESCOLA"]
                        school_name = row["NM_ESCOLA"]
                        class_code = row["CD_TURMA"]
                        class_name = row["NM_TURMA"]
                        grade_name = row["CD_ETAPA"]
                        shift_name = row["DC_TURNO"]
                        student_enrolment = row["CD_INSTITUCIONAL_ALUNO"]
                        student_name = row["NM_ALUNO"]
                        birth_date = row["DT_NASCIMENTO"]

                        unity, unity_created = Unity.objects.update_or_create(
                            client=client,
                            name=school_name,
                            unity_type=Unity.SUBSIDIARY
                        )

                        coordination, coordination_created = SchoolCoordination.objects.update_or_create(
                            name=school_name,
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
                            username=f'{unity_code}@rioeduca.net'
                        ).first()

                        if not coordination_user:
                            coordination_user = User.objects.create(
                                username=f'{unity_code}@rioeduca.net',
                                name=school_name,
                                email=f'{unity_code}@rioeduca.net',
                                must_change_password=True,
                                is_active=True
                            )

                        coordination_user.set_password(code_school)
                        coordination_user.save()

                        CoordinationMember.objects.update_or_create(
                            coordination=coordination,
                            user=coordination_user,
                            is_coordinator=True,
                            is_reviewer=True,
                            is_pedagogic_reviewer=True
                        )

                        print(f'{unity_code}, {code_school}')

                        grade = Grade.objects.get(
                            name=grade_name[0],
                            level__in=[Grade.ELEMENTARY_SCHOOL, Grade.ELEMENTARY_SCHOOL_2]
                        )

                        turns_dict = {
                            "Manhã":SchoolClass.MORNING,
                            "Tarde":SchoolClass.AFTERNOON,
                            "Integral":SchoolClass.ALL
                        }

                        school_class, school_class_created = SchoolClass.objects.update_or_create(
                            name=class_name,
                            grade=grade,
                            coordination=coordination,
                            class_type=SchoolClass.REGULAR,
                            school_year=2022,
                            turn=turns_dict[shift_name],
                            id_erp=class_code
                        )

                        student, student_created = Student.objects.update_or_create(
                            client=coordination.unity.client,
                            name=student_name,
                            enrollment_number=student_enrolment,
                            email=f'{student_enrolment}@alunorio.com.br',
                            id_erp=student_enrolment
                        )

                        school_class.students.add(student)
