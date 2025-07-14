from django.core.management.base import BaseCommand
from django.db import IntegrityError
from django.db.models import Q

from fiscallizeon.accounts.models import User
from fiscallizeon.clients.models import Client


class Command(BaseCommand):
    help = 'Atualiza username de alunos para novo modelo com código da escola'

    def add_arguments(self, parser):
        parser.add_argument('client_id', nargs=1, type=str)

    def handle(self, *args, **kwargs):
        client = Client.objects.get(pk=kwargs['client_id'][0])

        if not client.code:
            print("Cliente não possui")
            return

        students = client.student_set.all()

        for student in students:
            # check if string start with client code
            if student.user.username.startswith(f'{client.code}-') and not '@' in student.user.username:
                print(f"{student.username} já possui o código: {client.code}")
                continue

            student.user.username = f'{client.code}-{student.user.username}'
            student.user.save()