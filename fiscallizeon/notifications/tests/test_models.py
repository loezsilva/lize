from django.test import TestCase
from ..models import Notification, NotificationUser
from django.db.models import Field

class NotificationUserTeste(TestCase):
    def test_campo_nao_pode_ser_null(self):
        """
            Teste simples para impedir que o campo seja null
            
            Esse teste tem influência nos seguintes arquivos: [
                fiscallizeon/notifications/functions.py,
            ]
        """
        
        notification_user = NotificationUser()
        
        self.assertFalse(notification_user._meta.get_field('next_nps_date').null, f"O campo precisa ser null=False")