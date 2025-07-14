import csv
from datetime import datetime

from fiscallizeon.clients.models import Client, Unity
from fiscallizeon.applications.models import Application
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.students.models import Student
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.exams.models import Exam

from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Cadastra aplicações (considerando as unidades) a partir de um CSV'

    APPLICATIONS_FILE = 'applications.csv'

    def add_arguments(self, parser):
        parser.add_argument('client_id', nargs=1, type=str)

    def handle(self, *args, **kwargs):
        client = Client.objects.get(pk=kwargs['client_id'][0])

        with open(self.APPLICATIONS_FILE) as csvfile:
            reader = csv.DictReader(csvfile, delimiter=",")
            applications = list(reader)

        orientations = ''

        for application_csv in applications:
            exam = Exam.objects.filter(
                name=application_csv['exam'].strip(),
                coordinations__unity__client=client,
            ).distinct().first()

            date = datetime.strptime(application_csv['date'], '%d/%m/%Y'.strip())
            start = datetime.strptime(application_csv['start'], '%H:%M'.strip())
            end = datetime.strptime(application_csv['end'], '%H:%M'.strip())

            min_time_finish = datetime.strptime(application_csv['min_finish'], '%H:%M:%S'.strip())
            min_time_pause = datetime.strptime(application_csv['min_pause'], '%H:%M:%S'.strip())
            max_time_tolerance = datetime.strptime(application_csv['tolerance'], '%H:%M:%S'.strip())

            application, created = Application.objects.get_or_create(
                exam=exam,
                date=date.date(),
                start=start.time(),
                end=end.time(),
                min_time_finish=min_time_finish.time(),
                min_time_pause=min_time_pause.time(),
                max_time_tolerance=max_time_tolerance.time(),
                block_after_tolerance=bool(int(application_csv['block'])),
                subject=application_csv['subjects'].strip(),
                orientations=orientations,
                student_stats_permission_date=datetime(year=2030, month=12, day=31).date(),
            )

            if created:
                unity = Unity.objects.get(
                    name=application_csv['unity'].strip(),
                    client=client,
                )

                school_class = SchoolClass.objects.get(
                    name=application_csv['school_class'].strip(),
                    coordination__unity__client=client,
                    coordination__unity=unity,
                )

                students = Student.objects.filter(classes=school_class)

                application.school_classes.add(school_class)               
                application.students.set(students)

                inspectors_csv = application_csv['inspectors'].split(',')
                
                for inspector_csv in inspectors_csv:
                    inspector = Inspector.objects.get(email=inspector_csv.strip())
                    application.inspectors.add(inspector)

                print("Aplicação: ", application.exam)