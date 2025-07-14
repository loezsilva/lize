from django.core.management.base import BaseCommand
from fiscallizeon.analytics.models import GenericPerformances
from fiscallizeon.inspectors.models import TeacherSubject
from fiscallizeon.integrations.models import SubjectCode
from fiscallizeon.questions.models import Question
from fiscallizeon.subjects.models import Subject, Topic
from fiscallizeon.bncc.models import Abiliity, Competence

class Command(BaseCommand):
    help = 'Remove duplicatas de disciplinas da Lize'

    def handle(self, *args, **kwargs):
        try:
            incorrect_subject = Subject.objects.get(id='6650eed3-3667-42ab-84d0-371efedf0355')
            correct_subject = Subject.objects.get(id='b48637e8-fd75-497a-9901-55797ebda800')

            TeacherSubject.objects.filter(subject=incorrect_subject).update(subject=correct_subject)
            Question.objects.filter(subject=incorrect_subject).update(subject=correct_subject)
            Topic.objects.filter(subject=incorrect_subject).update(subject=correct_subject)
            Abiliity.objects.filter(subject=incorrect_subject).update(subject=correct_subject)
            Competence.objects.filter(subject=incorrect_subject).update(subject=correct_subject)
            GenericPerformances.objects.filter(subject=incorrect_subject).update(subject=correct_subject)
            SubjectCode.objects.filter(subject=incorrect_subject).update(subject=correct_subject)
            Subject.objects.filter(parent_subject=incorrect_subject).update(parent_subject=correct_subject)
            
            incorrect_subject.delete()
            
            print("concluído")

        except:
            
            print("O processo já foi concluído")
