import time
from sys import stdout

from fiscallizeon.core.utils import round_half_up
from django.core.management.base import BaseCommand

from fiscallizeon.exams.models import Exam
from fiscallizeon.clients.models import Client
from fiscallizeon.answers.models import OptionAnswer, TextualAnswer, FileAnswer, Attachments

class Command(BaseCommand):
    help = 'Gera performance de todos os exams do ano atual'

    def add_arguments(self, parser):
        parser.add_argument('--month', type=str, help='Mês que deseja gerar as performance')
        parser.add_argument('--client', type=str, help='ID do cliente que deseja gerar as performances')
    
    def handle(self, *args, **kwargs):

        month = int(kwargs['month'])
        client = None
        
        if kwargs['client']:
            client = Client.objects.get(pk=(kwargs['client']))


        option_answers_exams = OptionAnswer.objects.filter(
            created_at__year=2023, 
            created_at__month=month
        ).distinct('student_application__application__exam').values_list('student_application__application__exam__pk', flat=True)

        file_answers_exams = FileAnswer.objects.filter(
            created_at__year=2023, 
            created_at__month=month
        ).distinct('student_application__application__exam').values_list('student_application__application__exam__pk', flat=True)

        textual_answers_exams = TextualAnswer.objects.filter(
            created_at__year=2023, 
            created_at__month=month
        ).distinct('student_application__application__exam').values_list('student_application__application__exam__pk', flat=True)

        attachement_answers_exams = Attachments.objects.filter(
            created_at__year=2023, 
            created_at__month=month
        ).distinct('application_student__application__exam').values_list('application_student__application__exam__pk', flat=True)

        all_pk_exams = option_answers_exams.union(file_answers_exams).union(textual_answers_exams).union(attachement_answers_exams)
        
        exams = Exam.objects.filter(
            pk__in=all_pk_exams,
        ).distinct().order_by("-created_at")

        if client:
            exams = exams.filter(
                coordinations__unity__client=client
            )

        count = exams.count()
        stdout.write(f"\nQuandidade de exams encontrados: {count}")
        stdout.write(f"\nIniciando...")

        for index, exam in enumerate(exams):
            start_time = time.time()
            stdout.write(f"\nGerando a performance do caderno {exam}")
            exam.generate_performances(recalculate=True)
            stdout.write(f'\nCaderno {index+1}/{count}: {exam} demorou: {round_half_up((time.time() - start_time), 2)} segundos')