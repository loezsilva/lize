from django.core.management.base import BaseCommand
from django.test import Client
from django.db import IntegrityError
from django.db.models import Q

from fiscallizeon.accounts.models import User


class Command(BaseCommand):
    help = 'Atualiza usuários de coordenação, fiscais e professores para trocarem a senha no próximo acesso'

    def handle(self, *args, **kwargs):
        client = Client()
        users = User.objects.filter(
            Q(student__isnull=True) &
            Q(
                Q(coordination_member__isnull=False) |
                Q(inspector__isnull=False)
            )            
        ).distinct()

        count = 0
        for user in users[:100]:
            has_default_pass = client.login(username=user.email, password='fiscallize2021')
            has_email_pass = client.login(username=user.email, password=user.email)

            if has_default_pass or has_email_pass:
                print(user.email)

                user.must_change_password = True
                user.save()

                count += 1

        print(f'{count} usuários atualizados!')

            