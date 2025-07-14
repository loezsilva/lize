from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin

from rest_framework.generics import RetrieveUpdateAPIView

from fiscallizeon.exams.models import ClientCustomPage
from fiscallizeon.core.api import CsrfExemptSessionAuthentication

from fiscallizeon.exams.serializers.client_custom_page import ClientCustomPageSerializer

class ClientCustomPageRetrieveUpdateAPIView(LoginRequiredMixin, RetrieveUpdateAPIView):
    queryset = ClientCustomPage.objects.all()
    serializer_class = ClientCustomPageSerializer
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    authentication_classes = [CsrfExemptSessionAuthentication]