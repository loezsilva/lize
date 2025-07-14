from typing import Any, Optional
from django.core.management.base import BaseCommand, CommandParser

from fiscallizeon.accounts.models import User
from fiscallizeon.clients.models import Client, SchoolCoordination, CoordinationMember
from django.db.models import Q
from django.apps import apps


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser):
        parser.add_argument("--pk", action='append', type=str)

    def handle(self, *args, **kwargs):
        client = kwargs.get('pk')[0]
        User = apps.get_model("accounts", "User")

        User.objects.filter(
            Q(student__client=client) |
            Q(inspector__coordinations__unity__client=client) |
            Q(coordination_member__coordination__unity__client=client)
        ).distinct().update(is_active=True, temporarily_inactive=False)

