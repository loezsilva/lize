import csv

from django.core.management.base import BaseCommand
from django.utils import timezone

from fiscallizeon.subjects.models import Subject
from fiscallizeon.bncc.models import Competence, Abiliity
from fiscallizeon.clients.models import Client

class Command(BaseCommand):
    help = 'Copia BNCC de uma ou mais disciplinas para outra'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **kwargs):
        source_subjects = ["3849a9b1-8ced-47e8-87ba-402e57e64b55", "363ebe1c-b73f-4c5e-89e6-4ffb72d9e15c"]
        
        to_subject = Subject.objects.get(pk="a48fa6b4-d89a-40cd-84f2-39fc7fb159fb")
        original_abilities =  Abiliity.objects.filter(subject__in=source_subjects)
        original_competences = Competence.objects.filter(subject__in=source_subjects)

        client = Client.objects.get(pk="a2b1158b-367a-40a4-8413-9897057c8aa2")


        for abilitie in original_abilities:
            new_abilitie = Abiliity.objects.get(pk=abilitie.pk)
            new_abilitie.pk = None
            new_abilitie.subject = to_subject
            new_abilitie.knowledge_area = to_subject.knowledge_area
            new_abilitie.client = client
            new_abilitie.save(skip_hooks=True)

        for competence in original_competences:
            new_competence = Competence.objects.get(pk=competence.pk)
            new_competence.pk = None
            new_competence.subject = to_subject
            new_competence.knowledge_area = to_subject.knowledge_area
            new_competence.client = client
            new_competence.save(skip_hooks=True)