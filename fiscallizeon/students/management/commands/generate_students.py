import requests
import random

from django.core.management.base import BaseCommand
from django.utils import timezone

from fiscallizeon.students.models import Student
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.clients.models import Client
from fiscallizeon.accounts.models import User

from scraproxy import Scraproxy

class Command(BaseCommand):
    help = 'Gera cadastro de novos alunos'

    def add_arguments(self, parser):
        parser.add_argument('quantity', nargs='+', type=int)

    def handle(self, *args, **kwargs):
        client = Client.objects.first()
        school_class = SchoolClass.objects.first()

        # sp = Scraproxy()
        # sp.fetch_proxies(only_https=True, allow_transparent=False)

        for q in range(kwargs['quantity'][0]):
            
            try:
                # proxy = sp.random_proxy()
                
                student_data = requests.get("https://api.namefake.com/").json()

                enrollment_number = random.randrange(10000000, 99999999)
                email = f'{student_data["email_u"]}@{student_data["email_d"]}'
                name = student_data['name'].replace("Mrs. ", "").replace("Mr. ", "").replace("Prof. ", "").replace("Ms. ", "")

                user = User.objects.create_user(
                    email=email,
                    username=email,
                    password=enrollment_number,
                )

                student = Student(
                    client=client,
                    name=name,
                    enrollment_number=enrollment_number,
                    email=email,
                    user = user
                )
                student.save(skip_hooks=True)

                school_class.students.add(student)

                print(f'{name}, {email}, {enrollment_number}')

            except Exception as e:
                print(e)
            