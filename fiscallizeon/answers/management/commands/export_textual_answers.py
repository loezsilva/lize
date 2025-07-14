import csv
import datetime
from pytz import timezone

from django.core.management.base import BaseCommand

from fiscallizeon.answers.models import FileAnswer, TextualAnswer
from fiscallizeon.exams.models import ExamQuestion


class Command(BaseCommand):
    help = 'Exportar correções de monitores do ph'

    def add_arguments(self, parser):
        parser.add_argument('--question_id', type=str)

    def handle(self, *args, **kwargs):
        question_id = kwargs.get("question_id", None)

        textual_answers = TextualAnswer.objects.filter(
            question=question_id,
            created_at__year=datetime.datetime.now().year
        ).distinct()

        print("totals", textual_answers.count())

        with open('tmp/students-answers.csv', 'w') as csvfile:
            fieldnames = ["aluno","matricula", "email", "turma", "resposta"]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for textual_answer in textual_answers:
                result = {
                    'aluno':textual_answer.student_application.student.name,
                    'matricula': textual_answer.student_application.student.enrollment_number,
                    'email': textual_answer.student_application.student.email,
                    'turma': textual_answer.student_application.get_last_class_student(),
                    'resposta': textual_answer.content,
                }

                writer.writerow(result)
