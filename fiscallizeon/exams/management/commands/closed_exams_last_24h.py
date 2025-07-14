from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from fiscallizeon.exams.models import Exam
from django.template.loader import get_template
from fiscallizeon.core.threadings.sendemail import EmailThread
from django.conf import settings

class Command(BaseCommand):
    help = "Busca todos os cadernos que foram fechados nas últimas 24 horas."

    def handle(self, *args, **kwargs):
        now = timezone.now()
        past_24_hours = now - timedelta(hours=24)

        closed_exams = Exam.objects.filter(status=Exam.CLOSED, updated_at__gte=past_24_hours)

        closed_exams_history = []
        for exam in closed_exams:
            last_history = exam.history.filter(status=Exam.CLOSED).order_by('-history_date').first()

            if last_history and past_24_hours <= last_history.history_date <= now:
                closed_exams_history.append(exam)

        if closed_exams_history:
            self.stdout.write(f"Total de cadernos fechados nas últimas 24 horas: {len(closed_exams_history)}")
            for exam in closed_exams_history:
                formatted_date = exam.updated_at.strftime('%d/%m/%Y %H:%M:%S') 
                self.stdout.write(f"Caderno: {exam.name}, Fechado em: {formatted_date}")
                for teacher_subject in exam.teacher_subjects.all():
                    self.send_email(teacher_subject.teacher)

        else:
            self.stdout.write("Nenhum caderno foi fechado nas últimas 24 horas.")

    def send_email(self, teacher):
            
        template = get_template('mail_template/send_to_teacher_exams_closed_exams_last_24h.html')
        html = template.render({
            "teacher": teacher.name,
            "BASE_URL": settings.BASE_URL,
        })
        subject = f'LIZE: Você tem cadernos fechados para revisar'
        
        to = [teacher.email]

        EmailThread(subject, html, to).start()
