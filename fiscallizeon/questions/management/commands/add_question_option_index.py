import re
import glob
import json
import unicodedata
import html
# from html.parser import HTMLParser

from django.core.management.base import BaseCommand
from django.db.models import F, Window
from django.db.models.functions import Rank

from fiscallizeon.questions.models import Question, QuestionOption


class Command(BaseCommand):
    help = 'Adiciona índice às alternativas de questões objetivas'
   
    def handle(self, *args, **kwargs):
        questions = Question.objects.filter(category=Question.CHOICE)
        for question in questions.filter(created_at__year=2022):
            alternatives = question.alternatives.all().annotate(
                rank=Window(
                    expression=Rank(),
                    order_by=F('created_at').asc(),
                )
            )

            for alternative in alternatives:
                alternative.index = alternative.rank
                alternative.save()

            print(f'Question {question.pk} updated')