import csv
import os
import requests
import shutil
from datetime import datetime
from django.db import transaction
from django.core.management.base import BaseCommand

from fiscallizeon.clients.models import Client
from fiscallizeon.students.models import Student

class Command(BaseCommand):
    def add_arguments(self, parser):
        # parser.add_argument('--path_file', nargs=1, type=str)
        pass

    def handle(self, *args, **kwargs):
        client = Client.objects.get(pk="a2b1158b-367a-40a4-8413-9897057c8aa2") # Rede decisão
        # path_file = kwargs['path_file'][0]

        with requests.get('https://fiscallizeremote.nyc3.cdn.digitaloceanspaces.com/temp/alunos-decisao.csv', stream=True) as r:
            tmp_file = os.path.join("/tmp/students_responsible_emails.csv")
            print("baixou o arquivo")

            with open(tmp_file, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
                print("copiou")

            with open(tmp_file, 'r') as file:
                csvreader = csv.DictReader(file)
                with transaction.atomic():
                    students = Student.objects.filter(client=client)
                    
                    for row in csvreader:
                        matricula = row["matricula"]
                        email_responsavel = row["e-mail do responsável"]
                        if student := students.filter(enrollment_number=matricula).first():
                            student.responsible_email = email_responsavel
                            student.save(skip_hooks=True)
                            print(f"student: {student.name}, email resposável antigo: {student.responsible_email} alterado para: email responsável: {email_responsavel}")