import requests
import random

from django.core.management.base import BaseCommand

from fiscallizeon.students.models import Student
from fiscallizeon.clients.models import Client
from fiscallizeon.accounts.models import User
from fiscallizeon.inspectors.models import Inspector

from django.db import transaction


class Command(BaseCommand):
    help = 'Anonimiza dados de alunos, fiscais e clientes'

    def add_arguments(self, parser):
        # parser.add_argument('quantity', nargs='+', type=int)
        pass

    def handle(self, *args, **kwargs):
       # inspectors = Inspector.objects.all()
        clients = Client.objects.filter(pk="60c76b23-e58e-44de-997f-821f3b26993d")
        students = Student.objects.filter(client__in=clients)

        with transaction.atomic():
            for student in students:
                try:
                    student_data = requests.get("https://api.namefake.com/").json()

                    student.name = student_data['name'].replace("Mrs. ", "").replace("Mr. ", "").replace("Prof. ", "").replace("Ms. ", "")
                    student.enrollment_number = random.randrange(10000000, 99999999)
                    student.email = f'{student_data["email_u"]}@{student_data["email_d"]}'
                    student.save(skip_hooks=True)

                    student.user.name = student.name
                    student.user.username = student.email
                    student.user.email = student.email
                    student.user.set_password(f'pass-{student.enrollment_number}')
                    student.user.save()

                    print(f'Aluno - {student.name}, {student.email}, {student.enrollment_number}')

                except Exception as e:
                    print(e)

            # for inspector in inspectors:
            #     try:
            #         inspector_data = requests.get("https://api.namefake.com/").json()
                    
            #         inspector.name = inspector_data['name'].replace("Mrs. ", "").replace("Mr. ", "").replace("Prof. ", "").replace("Ms. ", "")
            #         inspector.email = f'{inspector_data["email_u"]}@{inspector_data["email_d"]}'
            #         inspector.save(skip_hooks=True)

            #         inspector.user.name = inspector.name
            #         inspector.user.username = inspector.email
            #         inspector.user.email = inspector.email
            #         inspector.user.set_password(inspector.email)
            #         inspector.user.save(skip_hooks=True)

            #         print(f'Fiscal - {inspector.name}, {inspector.email}')

            #     except Exception as e:
            #         print(e)

            for index, client in enumerate(clients, start=1):
                client.name = f'Cliente {index}'
                client.social_name = f'Cliente {index}'
                client.cnpj = "111111111111"
                
                for index_unities, unity in enumerate(client.unities.all(), start=1):
                    unity.name = f'Unidade {index_unities} do Cliente {index}'
                    unity.save(skip_hooks=True)

                    for index_coordination, coordination in enumerate(unity.coordinations.all(), start=1):
                        coordination.name = f'Coordenação {index_coordination} da {unity.name} '
                        coordination.responsible_name = "Responsavel"
                        coordination.responsible_email = "resp@email.com"
                        coordination.responsible_phone = "(84) 987745462"

                        coordination.save()

                client.save()
                print(f'Cliente - {client.name}')
