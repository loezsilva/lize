from datetime import datetime

from django.core.management.base import BaseCommand

from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.omrnps.models import NPSApplication, ClassApplication, TeacherOrder

class Command(BaseCommand):
    help = 'Edita NPS baseado em seu ID. Apaga as turmas e professores das séries informadas e recria'

    def add_arguments(self, parser):
        parser.add_argument('--id', nargs=1, type=str)
        parser.add_argument('--grade', nargs='+', type=str)

    def handle(self, *args, **kwargs):
        nps_application = NPSApplication.objects.get(
            id=kwargs['id'][0],
        )

        teachers_orders_delete = TeacherOrder.objects.filter(
            class_application__school_class__grade__in=kwargs['grade'],
            class_application__nps_application=nps_application,
        ).delete()
        class_applications = ClassApplication.objects.filter(
            school_class__grade__in=kwargs['grade'],
            nps_application=nps_application,
        )

        unity = class_applications.first().school_class.coordination.unity_id
        class_applications_delete = class_applications.delete()

        print("DELETED:", teachers_orders_delete)
        print("DELETED:", class_applications_delete)
        
        school_classes = SchoolClass.objects.filter(
            coordination__unity=unity,
            grade__in=kwargs['grade'],
            school_year=datetime.now().date().year,
        )

        for school_class in school_classes:
            ClassApplication.objects.create(
                nps_application=nps_application,
                school_class=school_class
            )

        print(f'Recriadas {school_classes.count()} turmas na aplicação de NPS')