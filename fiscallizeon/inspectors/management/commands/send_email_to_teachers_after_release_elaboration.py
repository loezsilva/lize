from django.core.management.base import BaseCommand

from django.utils import timezone
from fiscallizeon.exams.models import Exam, ExamTeacherSubject

class Command(BaseCommand):
    
    def handle(self, *args, **kwargs):
        """"
        Este commando precisa ser rodado após as 00:00 para um melhor funcionamento, pois ele é responsável por 
        notificar os professores quando há provas liberadas para ele elaborar.
        """
        
        today = timezone.now()

        exams = Exam.objects.filter(
            is_abstract=False,
            status=Exam.ELABORATING,
            created_at__year=today.year,
            release_elaboration_teacher=today.date()
        ).distinct()

        exam_teachers_subjects = ExamTeacherSubject.objects.filter(
            exam__in=exams, 
            examquestion__isnull=True,
            elaboration_email_sent=False
        ).distinct()
        
        for exam_teacher_subject in exam_teachers_subjects:
            exam_teacher_subject.send_email_to_teacher()