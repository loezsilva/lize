from django.db.models import Q, F
from django.utils import timezone
from datetime import timedelta, datetime
from django.core.management.base import BaseCommand

from django.template.loader import get_template
from fiscallizeon.core.threadings.sendemail import EmailThread
from fiscallizeon.parents.models import Parent

from django.conf import settings

from fiscallizeon.applications.models import Application, ApplicationStudent
import logging
logger = logging.getLogger()

class Command(BaseCommand):
    help = 'Envia email para os pais'
    sended_to_parents = []
    application_students = None

    def add_arguments(self, parser):
        parser.add_argument('--client', type=str, help='ID do cliente')
        parser.add_argument('--unity', type=str, help='ID da unidade')
        parser.add_argument('--day', type=str, help='(dd-mm-yyyy) Dia de liberação do caderno que deverá ser enviado notificação para os pais')
        
    def send_email(self, application_student):
        responsible_email = application_student.student.responsible_email
        responsible_email_two = application_student.student.responsible_email_two
        responsible_email_three = application_student.student.responsible_email_three
        responsible_email_four = application_student.student.responsible_email_four

        if not responsible_email in self.sended_to_parents or not responsible_email_two in self.sended_to_parents or not responsible_email_three in self.sended_to_parents or not responsible_email_four in self.sended_to_parents:
            try:
                if responsible_email:
                    parent_one, created_one = Parent.objects.get_or_create(
                        email=responsible_email
                    )
                    if parent_one.user:
                        parent_one.notify_parent_when_result_is_open()
                    else:
                        if not parent_one.hash_is_valid:
                            parent_one.send_mail_to_first_access()
                
                if responsible_email_two:
                    parent_two, created_two = Parent.objects.get_or_create(
                        email=responsible_email
                    )
                    if parent_two.user:
                        parent_two.notify_parent_when_result_is_open()
                    else:
                        if not parent_two.hash_is_valid:
                            parent_two.send_mail_to_first_access()

                if responsible_email_three:
                    parent_three, created_three = Parent.objects.get_or_create(
                        email=responsible_email
                    )
                    if parent_three.user:
                        parent_three.notify_parent_when_result_is_open()
                    else:
                        if not parent_three.hash_is_valid:
                            parent_three.send_mail_to_first_access()
                
                if responsible_email_four:
                    parent_four, created_four = Parent.objects.get_or_create(
                        email=responsible_email
                    )
                    if parent_four.user:
                        parent_four.notify_parent_when_result_is_open()
                    else:
                        if not parent_four.hash_is_valid:
                            parent_four.send_mail_to_first_access()
                    
                self.application_students.filter(student=application_student.student).update(email_sended_to_parent=True)
                    
            except Exception as e:
                logger.error(repr(e))
                print(f"Erro ao enviar o email para os pais da application_student: {str(application_student.id)}", e)
            
            self.sended_to_parents.append(responsible_email)
            self.sended_to_parents.append(responsible_email_two)            
            self.sended_to_parents.append(responsible_email_three)
            self.sended_to_parents.append(responsible_email_four)



    def handle(self, *args, **kwargs):
        today = timezone.localtime(timezone.now())
        
        day = kwargs.get('day', None)
        unity = kwargs.get('unity', None)
        
        if day:
            today = datetime.strptime(str(day), '%d-%m-%Y')

        applications = Application.objects.filter(
            student_stats_permission_date__date=today.date(),
            duplicate_application=False,
        )

        client = kwargs.get('client', None)
        if client:
            applications = applications.filter(
                exam__coordinations__unity__client=str(client)
            )
        
        self.application_students = ApplicationStudent.objects.filter(
            Q(
                application__in=applications,
                email_sended_to_parent=False,
                student__responsible_email__isnull=False
            ),
            Q(student__classes__coordination__unity=unity) if unity else Q(),
            Q(
                Q(start_time__isnull=False) |
                Q(is_omr=True) | 
                Q(option_answers__isnull=False) |
                Q(textual_answers__isnull=False) |
                Q(file_answers__isnull=False)
            ) 
        ).distinct()
        
        for application_student in self.application_students:
            self.send_email(application_student=application_student)