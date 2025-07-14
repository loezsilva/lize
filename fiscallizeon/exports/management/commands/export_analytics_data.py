from datetime import datetime
import requests

import pandas as pd
from fastparquet import write

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models.functions import Cast, Coalesce, Concat
from django.db.models import CharField, F, Q, Subquery, OuterRef, Case, When, Value, DecimalField
from django.core.management.base import BaseCommand

from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.omr.models import OMRStudents, OMRError
from fiscallizeon.distribution.models import RoomDistribution
from fiscallizeon.students.models import Student
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.subjects.models import Subject, Topic
from fiscallizeon.clients.models import Client, SchoolCoordination, Unity
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.questions.models import Question
from fiscallizeon.bncc.models import Abiliity, Competence
from fiscallizeon.exams.models import Exam, ExamQuestion, ExamTeacherSubject, StatusQuestion
from fiscallizeon.answers.models import FileAnswer, TextualAnswer, OptionAnswer

class Command(BaseCommand):
    help = 'Exporta dados para planilha analítica'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.webhook = 'https://automation.queiroz.dev.br/webhook/bb42cc89-f75a-42fe-89fb-936ff1b5f519'

    def add_arguments(self, parser):
        now = datetime.now()
        parser.add_argument('month', nargs='?', const=now.month, default=now.month, type=int)
        parser.add_argument('year', nargs='?', const=now.year, default=now.year, type=int)
        parser.add_argument('client_pk', nargs='?', type=str)

    def handle(self, *args, **kwargs):
        self.month = kwargs['month']
        self.year = kwargs['year']

        if self.month == 1:
            self.month = 12
            self.year -= 1
        else:
            self.month -= 1

        print("### Iniciando exportação")
        if client_pk := kwargs['client_pk']:
            clients = Client.objects.filter(pk=client_pk).order_by('created_at')
        else:
            clients = Client.objects.all().order_by('created_at')

        export_data = []
        for client in clients:
            print(f"# Cliente {client}")
            applications = Application.objects.filter(
                exam__coordinations__unity__client=client,
                date__month=self.month,
                date__year=self.year,
            ).distinct()

            presential_applications = applications.filter(
                Q(answer_sheet__isnull=False) |
                Q(room_distribution__exams_bag__isnull=False)
            )

            remote_applications = applications.filter(
                category=Application.MONITORIN_EXAM,
            )

            homework_applications = applications.filter(
                category=Application.HOMEWORK,
            )

            omr_errors = OMRError.objects.filter(
                upload__user__coordination_member__coordination__unity__client=client,
                created_at__year=self.year,
                created_at__month=self.month,
                is_solved=True,
            ).distinct().count()

            exams = Exam.objects.filter(
                coordinations__unity__client=client,
                created_at__year=self.year,
                created_at__month=self.month,
            ).distinct().count()

            room_distributions = RoomDistribution.objects.filter(
                application__in=applications,
            ).distinct().count()

            questions = Question.objects.filter(
                coordinations__unity__client=client,
                created_at__year=self.year,
                created_at__month=self.month,
            ).distinct()

            file_answers = FileAnswer.objects.filter(
                Q(who_corrected__isnull=False),
                Q(created_at__year=self.year),
                Q(created_at__month=self.month),
                Q(
                    Q(student_application__application__in=remote_applications) |
                    Q(student_application__application__in=homework_applications)
                )
            ).distinct().count()

            textual_answers = TextualAnswer.objects.filter(
                Q(who_corrected__isnull=False),
                Q(created_at__year=self.year),
                Q(created_at__month=self.month),
                Q(
                    Q(student_application__application__in=remote_applications) |
                    Q(student_application__application__in=homework_applications)
                )
            ).distinct().count()

            active_students = Student.objects.filter(
                client=client,
                user__last_login__month=self.month,
                user__last_login__year=self.year,
            ).count()

            categorized_questions = questions.filter(
                Q(abilities__isnull=False) |
                Q(competences__isnull=False)
            )

            export_data.append({
                'client': client.name, 
                'month': self.month - 1,
                'generated_omr': ApplicationStudent.objects.filter(application__in=presential_applications).count(),
                'read_omr': OMRStudents.objects.filter(application_student__application__in=presential_applications).count(),
                'omr_error': omr_errors,
                'exams': exams,
                'remote_applications': ApplicationStudent.objects.filter(application__in=remote_applications, start_time__isnull=False).count(),
                'homework_applications': ApplicationStudent.objects.filter(application__in=homework_applications, start_time__isnull=False).count(),
                'room_distributions': room_distributions,
                'questions': questions.count(),
                'online_corrected': file_answers + textual_answers,
                'active_students': active_students,
                'categorized_questions': categorized_questions.count(),
            })

        response = requests.post(self.webhook, json=export_data)