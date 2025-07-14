from rest_framework.generics import CreateAPIView, UpdateAPIView
from django.conf import settings
from fiscallizeon.events.serializers import application_message
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.core.api import CsrfExemptSessionAuthentication

from rest_framework.authentication import BasicAuthentication 

class ApplicationMessageView(CreateAPIView):
    required_permissions = [settings.COORDINATION, settings.INSPECTOR, settings.TEACHER, ]
    serializer_class = application_message.ApplicationMessageSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def perform_create(self, serializer):
        serializer.save(
            sender=self.request.user,
        )

aplication_message_create = ApplicationMessageView.as_view()