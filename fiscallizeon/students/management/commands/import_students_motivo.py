import requests
import random
import uuid
import csv

from django.core.management.base import BaseCommand
from django.utils import timezone
from fiscallizeon.accounts.models import User
from fiscallizeon.students.models import Student
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.clients.models import Client, SchoolCoordination

from scraproxy import Scraproxy

class Command(BaseCommand):
    help = 'Importa alunos da planilha do MOTIVO'

    STUDENTS_FILE = 'alunos_motivo.csv'

    def add_arguments(self, parser):
        parser.add_argument('client_id', nargs=1, type=str)
        parser.add_argument('coordination_id', nargs=1, type=str)

    def handle(self, *args, **kwargs):
        try:
            client = Client.objects.get(pk=kwargs['client_id'][0])
            coordination = SchoolCoordination.objects.get(pk=kwargs['coordination_id'][0])

            with open(self.STUDENTS_FILE) as csvfile:
                reader = csv.DictReader(csvfile, delimiter=",")
                students = list(reader)

            for student in students:
                user, _ = User.objects.get_or_create(
                    username=student['LOGIN'], 
                    defaults={
                        'name': student['NOME'],
                        'email': f'{student["LOGIN"]}@emailpadrao.com'
                    }
                )

                user.set_password(student['SENHA'])
                user.save()

                new_student, _ = Student.objects.update_or_create(
                    client=client,
                    user=user,
                    enrollment_number=student['MATRICULA'],
                    defaults={
                        'name': student['NOME'],
                        'email': f'{student["LOGIN"]}@emailpadrao.com',
                    }
                )

                school_class, _ = SchoolClass.objects.update_or_create(
                    name=student['TURMA'],
                    defaults={
                        'grade': student['TURMA'],
                        'coordination': coordination
                    }
                )

                if new_student not in school_class.students.all():
                    school_class.students.add(new_student)

        except Exception as e:
            print(e)
            