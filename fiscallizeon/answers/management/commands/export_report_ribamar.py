import csv
import datetime
from pytz import timezone

from django.core.management.base import BaseCommand

from fiscallizeon.classes.models import Grade
from fiscallizeon.clients.models import Unity
from fiscallizeon.applications.models import ApplicationStudent

class Command(BaseCommand):
    help = 'Exportar relatório de gabaritos do Ribamar'

    def handle(self, *args, **kwargs):
        client_ribamar_pk = "5bbe72b2-7a16-4f8c-969f-554a67719c87"
        application_students = ApplicationStudent.objects.filter(
            is_omr=True,
            student__client=client_ribamar_pk
        ).distinct()

        grades = Grade.objects.filter(
            level__in=[Grade.ELEMENTARY_SCHOOL, Grade.ELEMENTARY_SCHOOL_2]
        ).order_by('name').distinct()

        unities = Unity.objects.filter(
            client=client_ribamar_pk
        ).distinct()

        fieldnames = ['unidade', ]

        for grade in grades:
            fieldnames.append(grade.get_complete_name())

        with open('/code/tmp/ribamar_empty.csv', 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for unity in unities:
                result = {
                    'unidade':unity.name,
                }
                for grade in grades:
                    result[grade.get_complete_name()] = application_students.filter(
                        option_answers__isnull=True,
                        student__classes__grade=grade,
                        student__classes__coordination__unity=unity
                    ).distinct().count()
                writer.writerow(result)

        with open('/code/tmp/ribamar_corrected.csv', 'w') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for unity in unities:
                result = {
                    'unidade':unity.name,
                }
                for grade in grades:
                    result[grade.get_complete_name()] = application_students.filter(
                        student__classes__grade=grade,
                        option_answers__created_by__isnull=False,
                        student__classes__coordination__unity=unity,
                    ).distinct().count()
                writer.writerow(result)