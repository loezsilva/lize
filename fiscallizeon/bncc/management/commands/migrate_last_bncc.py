import csv
import re

from django.core.management.base import BaseCommand
from django.utils import timezone

from fiscallizeon.bncc.models import Abiliity, Competence

class Command(BaseCommand):
    help = 'Atualiza BNCC antiga para o novo modelo de subjects e knowledge area'


    def handle(self, *args, **kwargs):
        abilities = Abiliity.objects.filter(
            subject__isnull=False,
            knowledge_area__isnull=True
        )

        for ability in abilities:
            ability.knowledge_area = ability.subject.knowledge_area
            ability.save()

        competence = Competence.objects.filter(
            subject__isnull=False,
            knowledge_area__isnull=True
        )

        for competence in competence:
            competence.knowledge_area = competence.subject.knowledge_area
            competence.save()

        self.stdout.write(self.style.SUCCESS('Successfully updated BNCC'))