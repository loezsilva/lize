import os
import requests
import shutil
import csv, os, boto3
from decouple import config
from django.conf import settings
from django.core.management.base import BaseCommand

from fiscallizeon.clients.models import Client
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

            with open(tmp_file, 'r') as file:
                csvreader = csv.DictReader(file)
                with open('tmp/result-update-students-curia.csv', 'w') as csvfile:
                    fieldnames = ["nome", "matricula", "quantidade" ]

                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()

                    for index, row in enumerate(csvreader):
                        nome = row["nome"].replace("  ", " ").strip()
                        email = row["email"].replace("  ", " ").strip()
                        usuario = row["usuario"].replace("  ", " ").strip()
                        senha = row["senha"].replace("  ", " ").strip()
                        matricula = row["matricula"].replace("  ", " ").strip()

                        try:
                            students = Student.objects.filter(
                                client=client,
                                name__iexact=nome,
                                user__is_active=True
                            )

                            count = int(students.count())

                            result = {
                                "nome": nome,
                                "matricula": matricula,
                                "quantidade": count,
                            }

                            if count == 1:
                                # print(index, "salvou", nome, usuario, senha)
                                student = students.first()
                                student.enrollment_number = matricula
                                student.email = email
                                student.save(skip_hooks=True)
                                student.user.username = usuario
                                student.user.email = email
                                student.user.set_password(senha)
                                student.user.save()
                            else:
                                print(f'{nome}, {matricula}, {students.count()}')

                            writer.writerow(result)

                        except Exception as e:
                            print("@@@@@@@@@@@@@@@@@@@@" ,e)

            session = boto3.session.Session()
            s3 = session.resource(
                's3',
                region_name='nyc3',
                endpoint_url='https://nyc3.digitaloceanspaces.com',
                aws_access_key_id=config('AWS_ACCESS_KEY_ID'),
                aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY'),
            )

            path = os.path.join(settings.BASE_DIR, 'tmp/result-update-students-curia.csv')
            
            s3.meta.client.upload_file(
                Filename=path,
                Bucket=config('AWS_STORAGE_BUCKET_NAME'),
                Key=f'temp/result-update-students-curia.csv'
            )
