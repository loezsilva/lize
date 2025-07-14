import glob
import json
import random

from django.forms.models import model_to_dict
from django.core.management.base import BaseCommand

from fiscallizeon.exams.models import Exam
from fiscallizeon.questions.models import Question


class Command(BaseCommand):
    help = 'Mistura alternativas das questões discursivas de uma prova'

    def add_arguments(self, parser):
        parser.add_argument('exam_pk', nargs='+', type=str)

    def handle(self, *args, **kwargs):
        exam_pk = kwargs.get('exam_pk')[0]
        exam = Exam.objects.get(pk=exam_pk)
        choice_questions = exam.questions.filter(category=Question.CHOICE)

        for question in choice_questions:
            print(f'Shuffling question {question.pk} alternatives')
            try:
                alternatives = question.alternatives.all()
                correct_alternative = alternatives.filter(is_correct=True).first()
                random_alternative = random.choice(alternatives)
                random_alternative_data = model_to_dict(random_alternative)
                random_alternative.text = correct_alternative.text
                random_alternative.is_correct = correct_alternative.is_correct
                correct_alternative.text = random_alternative_data['text']
                correct_alternative.is_correct = random_alternative_data['is_correct']
                random_alternative.save()
                correct_alternative.save()
            except Exception as e:
                import sys, os
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(exc_type, fname, exc_tb.tb_lineno)
                print(e)