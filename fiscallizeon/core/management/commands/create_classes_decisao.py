import requests
import random

from django.core.management.base import BaseCommand

from fiscallizeon.clients.models import Client, SchoolCoordination
from fiscallizeon.classes.models import Grade, SchoolClass

from django.db import transaction


class Command(BaseCommand):
    help = 'Anonimiza dados de alunos, fiscais e clientes'

    def handle(self, *args, **kwargs):
        client = Client.objects.get(pk="a2b1158b-367a-40a4-8413-9897057c8aa2")
        grades = Grade.objects.all().exclude(
            name__icontains="Concurso"
        ).exclude(
            name__icontains="Curso"
        )
        with transaction.atomic():
            for grade in grades:
                for unity in client.unities.all(): 
                    coordination = SchoolCoordination.objects.filter(
                        unity=unity,
                        name__endswith=grade.get_level_display()[-4:].replace("2", "II").replace("1", "I")
                    ).first()

                    school_class_name = f'Turma Bolsa - {grade.get_complete_name()} - {unity.name}'
                    SchoolClass.objects.get_or_create(
                        name=school_class_name,
                        grade=grade,
                        coordination=coordination
                    )
                    print(school_class_name)


