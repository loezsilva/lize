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
import random

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--path_file', nargs=1, type=str)

    def handle(self, *args, **kwargs):

        
client = Client.objects.get(pk="5bbe72b2-7a16-4f8c-969f-554a67719c87") #ID do curiar
path_file = "https://fiscallizeremote.nyc3.cdn.digitaloceanspaces.com/temp/alunos-curia-2024%20-%20Planilha1.csv"
with requests.get(path_file, stream=True) as r:
    tmp_file = os.path.join("/tmp/curiar.csv")
    print("baixou o arquivo")
    with open(tmp_file, 'wb') as f:
        shutil.copyfileobj(r.raw, f)
        print("copiou")
    with open(tmp_file, 'r') as file:
        with transaction.atomic():
            csvreader = csv.DictReader(file)
            for index, row in enumerate(csvreader):
                student_name = row["NOME"].upper()
                print(index, student_name)
                grade_name = row["ANO"].upper()
                shift_name = row["TURNO"].upper()
                class_name = row["TURMA"].upper()
                school_name = row["UNIDADE"].upper()
                student_enrolment = random.random(999, 999999)
                date = row["NASCIMENTO"].upper()
                if not shift_name in class_name:
                    class_name = f'{class_name} {shift_name}'
                unity = Unity.objects.filter(
                    client=client,
                    name=school_name
                ).first()
                coordination = unity.coordinations.all().first()
                grade = Grade.objects.get(
                    name=grade_name[0],
                    level__in=[Grade.ELEMENTARY_SCHOOL, Grade.ELEMENTARY_SCHOOL_2]
                )
                turns_dict = {
                    "INTEGRAL":SchoolClass.ALL,
                    "MATUTINO":SchoolClass.MORNING,
                    "VESPERTINO":SchoolClass.AFTERNOON
                }
                school_class, school_class_created = SchoolClass.objects.update_or_create(
                    grade=grade,
                    name=class_name,
                    school_year=2024,
                    coordination=coordination,
                    turn=turns_dict[shift_name],
                    class_type=SchoolClass.REGULAR,
                )
                students = Student.objects.filter(
                    name=student_name,
                    client=coordination.unity.client,
                    enrollment_number__icontains=date.replace("/", "")
                )
                if not students or students.count() > 1:
                    student = Student.objects.create(
                        name=student_name,
                        id_erp=student_enrolment,
                        client=coordination.unity.client,
                        enrollment_number=f'{date.replace("/", "")}-{student_enrolment}',
                        email=f'{date.replace("/", "")}-{student_enrolment}@projetocuriar.com.br',
                    )
                if students and students.count() == 1:
                    student = students.first()
                user = User.objects.using('default').filter(student=student)
                user.is_active=True
                user.save()
                school_class.students.add(student)