from django.core.management.base import BaseCommand
from django.utils import timezone
from django.apps import apps
from django.conf import settings
from django.template.loader import get_template
from django.db.models import Count

from fiscallizeon.core.threadings.sendemail import EmailThread
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.exams.models import ExamTeacherSubject
from fiscallizeon.clients.models import Client, SchoolCoordination


class Command(BaseCommand):
    """
    Task: 86a7z8drt
    Envia email para professores que 
    possuem pendências de revisão em cadernos que ele foi inserido especificamente.
    """

    help = "Envia email para professores com pendências de revisão."

    def handle(self, *args, **options):

        exam_teacher_subjects = ExamTeacherSubject.objects.annotate(
            questions_count=Count('examquestion')
        ).filter(
            reviewed_by__isnull=False,
            exam__review_deadline__gte=timezone.now().date(),
            questions_count__gt=0,
            reviewer_email_sent=False
        ).distinct()

        for exam_teacher_subject in exam_teacher_subjects:

            exam_teacher_subject.send_email_to_teacher_reviewer()