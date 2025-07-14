from django.core.management.base import BaseCommand

from fiscallizeon.questions.models import Question
from fiscallizeon.inspectors.models import Inspector


class Command(BaseCommand):
    help = 'Migra questões publicas para um cliente'
   
    def handle(self, *args, **kwargs):
        questions = Question.objects.filter(is_public=True)
        user = Inspector.objects.get(pk="648e14fa-088e-45fb-ab9d-00d5ed20a41f").user
        for question in questions:
            question.duplicate_question(user=user)