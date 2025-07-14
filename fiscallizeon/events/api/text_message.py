from django.conf import settings
from rest_framework.generics import CreateAPIView, UpdateAPIView

from fiscallizeon.events.serializers import text_message
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.core.api import CsrfExemptSessionAuthentication

from rest_framework.authentication import BasicAuthentication 

class CreateTextMessageView(CreateAPIView):
    required_permissions = [settings.COORDINATION, settings.INSPECTOR, settings.STUDENT, settings.TEACHER, ]
    serializer_class = text_message.CreateTextMessageSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def perform_create(self, serializer):
        serializer.save(
            sender=self.request.user,
        )

text_message_create = CreateTextMessageView.as_view()