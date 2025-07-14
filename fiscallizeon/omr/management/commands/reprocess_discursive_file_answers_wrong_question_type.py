from django.db.models import F, Subquery, OuterRef
from django.db.models.functions import Round
from django.core.management.base import BaseCommand

from fiscallizeon.answers.models import FileAnswer
from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.questions.models import Question
from fiscallizeon.omr.tasks.fix_answers.reprocess_file_answers import reprocess_file_answers

class Command(BaseCommand):
    help = 'Reprocessa FileAnswers do decisão para questões do tipo Textual e ajusta grades errados'

    def handle(self, *args, **kwargs):
        file_answers = FileAnswer.objects.filter(
            student_application__student__client="a2b1158b-367a-40a4-8413-9897057c8aa2",
        ).exclude(question__category=Question.FILE)

        for file_answer in file_answers:
            print(f'Answer em fila: {file_answer.pk}')
            reprocess_file_answers.apply_async(
                args=[file_answer.pk],
            )