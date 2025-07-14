from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.template.loader import get_template
from django.db.models import Count, Q

from fiscallizeon.integrations.models import IntegrationToken
from fiscallizeon.clients.models import Client
from fiscallizeon.core.threadings.sendemail import EmailThread

class Command(BaseCommand):
    help = "Realiza verificações periódicas, incluindo tokens de integração expirados, quantidade máxima de alunos excedida e novos clientes cadastrados, enviando e-mails de notificação."


    def handle(self, *args, **options):
        today = timezone.localdate()

        def verify_tokens_expireds():
            token_clients_expired = IntegrationToken.objects.filter(expiration_date__lt=today)

            if token_clients_expired:
                template = get_template('notifications/send_notification_expired_token.html')
                html = template.render({"tokens": token_clients_expired})
                EmailThread('Token expirado', html, ['teste@teste.com']).start() # lembrar de altrar os emails para os reais

        def verify_max_students_quantity():
            clients = Client.objects.filter(max_students_quantity__isnull=False).annotate(
                active_students_count=Count('student', filter=Q(student__user__is_active=True))
            )

            clients_info = [
                {
                    'client': client,
                    'active_students_count': client.active_students_count,
                    'max_students_quantity': client.max_students_quantity
                }
                for client in clients if client.max_students_quantity < client.active_students_count
            ]
            if clients_info:

                template = get_template('notifications/send_notification_exceeded_max_student_quantity.html')
                html =  template.render({'client_info': clients_info})
                EmailThread('Quantidade máxima de alunos excedida', html, ['teste@teste.com']).start() # lembrar de alterar os emails para os reais
            
        def verify_new_registered_clients():
            new_clients = Client.objects.filter(created_at__date=today)

            if new_clients:
                template = get_template('notifications/send_notification_new_registered_clients.html')
                html = template.render({'new_clients': new_clients})
                EmailThread('Novos clientes Cadastrados!', html, ['teste@email.com']).start() # alterar o emails para os reais

        verify_tokens_expireds()
        verify_max_students_quantity()
        verify_new_registered_clients()
