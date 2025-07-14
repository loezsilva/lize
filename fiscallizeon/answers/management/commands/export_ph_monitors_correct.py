import csv
import datetime
from pytz import timezone

from django.core.management.base import BaseCommand

from fiscallizeon.answers.models import FileAnswer, TextualAnswer
from fiscallizeon.exams.models import ExamQuestion


class Command(BaseCommand):
    help = 'Exportar correções de monitores do ph'

    def handle(self, *args, **kwargs):
        date = datetime.datetime(2022, 10, 31, 00, 00, 00, tzinfo=timezone('America/Recife'))
        date_end = datetime.datetime(2022, 11, 28, 00, 00, 00, tzinfo=timezone('America/Recife'))


        fa = FileAnswer.objects.filter(
            updated_at__gte=date,
            updated_at__lte=date_end, 
            who_corrected__isnull=False, 
            student_application__student__client__name__icontains="ph",
            student_application__student__classes__school_year=2022

        ).only("question", "who_corrected", "student_application", "updated_at").distinct()

        ta = TextualAnswer.objects.filter(
            updated_at__gte=date, 
            updated_at__lte=date_end,  
            who_corrected__isnull=False, 
            student_application__student__client__name__icontains="ph",
            student_application__student__classes__school_year=2022
        ).only("question", "who_corrected", "student_application", "updated_at").distinct()

        totals = fa.union(ta).order_by("updated_at")

        print("totals", totals.count())

        with open('tmp/ph-nov.csv', 'w') as csvfile:
            fieldnames = ['monitor', 'iniciou', 'email', 'data', 'hora', 'aluno', 'caderno', 'disciplina', 'questão']

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            count = 1
            
            for total in totals:
                result = {
                    'monitor':total.who_corrected.name,
                    'iniciou': "sim" if total.student_application.start_time else "não",
                    'email':total.who_corrected.email,
                    'data':total.updated_at.date(),
                    'hora':total.updated_at.time(),
                    'aluno':total.student_application.student.name,
                    'caderno':total.student_application.application.exam.name,
                    'disciplina': total.question.subject.name,
                    'questão': total.student_application.application.exam.number_print_question(total.question)
                }
                writer.writerow(result)
                print(count, "-----")
                count = count + 1
