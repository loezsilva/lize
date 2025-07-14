import csv
import os
import requests
import shutil
from django.core.management.base import BaseCommand
from fiscallizeon.subjects.models import Subject
from fiscallizeon.clients.models import Client
from fiscallizeon.integrations.models import SubjectCode

class Command(BaseCommand):
    help = 'Importa tags das disciplinas'

    def add_arguments(self, parser):
        parser.add_argument('--path_file', nargs=1, type=str)

    def handle(self, *args, **kwargs):
        CLIENT_PK = 'a2b1158b-367a-40a4-8413-9897057c8aa2' # rede decisão
        
        path_file = kwargs['path_file'][0]


        with requests.get(path_file, stream=True) as r:
            
            tmp_file = os.path.join("/tmp/import_file.csv")

            with open(tmp_file, 'wb') as f:
                shutil.copyfileobj(r.raw, f)

            with open(tmp_file, 'r') as file:
                reader = csv.DictReader(file)
            
                for row in reader:
                    subject_name = row["Disciplina"]
                    code = row["Sigla Disciplina"]
                    if subjects := Subject.objects.filter(client=CLIENT_PK, name__iexact=subject_name).distinct():
                        for subject in subjects:
                            SubjectCode.objects.get_or_create(
                                client=Client.objects.get(pk=CLIENT_PK),
                                code=code,
                                subject=subject
                            )
