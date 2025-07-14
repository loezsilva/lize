from datetime import timedelta

from django.core.management.base import BaseCommand
from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.questions.models import Question
from fiscallizeon.core.utils import generate_random_string


class Command(BaseCommand):
    help = 'Marca com status de erro os OMRUpload que estão processando indefinidamente'

    def handle(self, *args, **kwargs):
        exam_questions = ExamQuestion.objects.filter(
            short_code__isnull=True,
            exam__is_abstract=True,
            question__category__in=[Question.TEXTUAL, Question.FILE],
            created_at__year__gte=2023    
        )
        for exam_question in exam_questions:
            exam_question.short_code = generate_random_string(4).upper()
            exam_question.save()
        print(exam_questions.count(), "questões atualizadas.")    