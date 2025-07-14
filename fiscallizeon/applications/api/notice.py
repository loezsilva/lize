from rest_framework import generics
from django.conf import settings
from fiscallizeon.applications.models import Annotation
from fiscallizeon.applications.serializers.notice import ApplicationNoticeSerializer
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.core.api import CsrfExemptSessionAuthentication

from rest_framework.authentication import BasicAuthentication 

from django.contrib.auth.mixins import LoginRequiredMixin

class ApplicationNoticeCreate(LoginRequiredMixin, CheckHasPermission, generics.CreateAPIView):
    required_permissions = [settings.COORDINATION, settings.INSPECTOR, settings.TEACHER, ]
    serializer_class = ApplicationNoticeSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def perform_create(self, serializer):
        serializer.save(
            inspector=self.request.user,
        )
        

application_notice_create_api = ApplicationNoticeCreate.as_view()
