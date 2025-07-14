import requests
import random
import uuid
import csv

from django.core.management.base import BaseCommand
from django.utils import timezone

from fiscallizeon.students.models import Student
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.clients.models import Client, SchoolCoordination

from scraproxy import Scraproxy

class Command(BaseCommand):
    help = 'Importa alunos da planilha do CEI'

    STUDENTS_FILE = 'alunos_cei.csv'

    def add_arguments(self, parser):
        parser.add_argument('client_id', nargs=1, type=str)
        parser.add_argument('coordination_id_fundamental', nargs=1, type=str)
        parser.add_argument('coordination_id_medio', nargs=1, type=str)

    def handle(self, *args, **kwargs):
        try:
            client = Client.objects.get(pk=kwargs['client_id'][0])
            coordination_fundamental = SchoolCoordination.objects.get(pk=kwargs['coordination_id_fundamental'][0])
            coordination_medio = SchoolCoordination.objects.get(pk=kwargs['coordination_id_medio'][0])

            with open(self.STUDENTS_FILE) as csvfile:
                reader = csv.DictReader(csvfile, delimiter=",")
                students = list(reader)

            for student in students:
                new_student, _ = Student.objects.update_or_create(
                    client=client,
                    enrollment_number=student['MATRICULA'],
                    defaults={
                        'name': student['ALUNO'],
                        'email': student['EMAIL'],
                    }
                )

                school_class, _ = SchoolClass.objects.update_or_create(
                    name=student['TURMA'],
                    defaults={
                        'grade': student['TURMA'][2],
                        'coordination': coordination_fundamental if student['TURMA'][0] == '1' else coordination_medio,
                    }
                )

                if new_student not in school_class.students.all():
                    school_class.students.add(new_student)

        except Exception as e:
            print(e)
            