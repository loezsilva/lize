from datetime import datetime

from django.core.management.base import BaseCommand

from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.clients.models import Client
from fiscallizeon.omrnps.models import NPSApplication, NPSAxis, NPSApplicationAxis, ClassApplication

class Command(BaseCommand):
    help = 'Cria um NPS baseado em uma série de um cliente'

    def add_arguments(self, parser):
        parser.add_argument('--name', nargs=1, type=str)
        parser.add_argument('--client', nargs=1, type=str)
        parser.add_argument('--unity', nargs='?', type=str)
        parser.add_argument('--grade', nargs='+', type=str)

    def handle(self, *args, **kwargs):
        nps_application = NPSApplication.objects.create(
            client=Client.objects.get(pk=kwargs['client'][0]),
            date=datetime.now().date(),
            name=kwargs['name'][0],
            show_teahcer_name=True
        )

        for index, axis in enumerate(NPSAxis.objects.all()):
            NPSApplicationAxis.objects.create(
                nps_axis=axis,
                nps_application=nps_application,
                order=index,
            )

        school_classes = SchoolClass.objects.filter(
            coordination__unity__client=kwargs['client'][0],
            grade__in=kwargs['grade'],
            school_year=datetime.now().date().year,
        )

        if kwargs['unity']:
            school_classes = school_classes.filter(
                coordination__unity=kwargs['unity']
            )

        for school_class in school_classes:
            ClassApplication.objects.create(
                nps_application=nps_application,
                school_class=school_class
            )

        print(f'Criadas {school_classes.count()} turmas na aplicação de NPS')