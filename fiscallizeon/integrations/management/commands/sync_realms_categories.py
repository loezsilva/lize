from typing import Any, Optional
from django.core.management.base import BaseCommand, CommandParser

from fiscallizeon.clients.models import Client
from fiscallizeon.subjects.models import Topic
from fiscallizeon.bncc.models import Abiliity, Competence
from django.db.models import Q
from django.apps import apps


class Command(BaseCommand):
    CLIENT_ID = "83579d53-7d1c-477d-aafc-09c3070bdb41"

    # def add_arguments(self, parser: CommandParser):
    #     parser.add_argument("--pk", action='append', type=str)

    def handle(self, *args, **kwargs):
        client = Client.objects.get(pk=self.CLIENT_ID)

        topics = Topic.objects.filter(
            client=client,
            codes__isnull=True,
        )

        abilities = Abiliity.objects.filter(
            Q(
                Q(client=client) |
                Q(client__isnull=True)
            ),
            Q(codes__isnull=True),
        )
        
        competences = Competence.objects.filter(
             Q(
                Q(client=client) |
                Q(client__isnull=True)
            ),
            Q(codes__isnull=True),
        )

        for topic in topics:
            topic.update_erp()
        
        for ability in abilities:
            if not ability.client:
                ability.client = client
 
            ability.update_erp()

        for competence in competences:
            if not ability.client:
                ability.client = client

            competence.update_erp()