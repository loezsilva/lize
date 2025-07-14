from django.conf import settings
from rest_framework import viewsets
from fiscallizeon.applications.models import RandomizationVersion
from fiscallizeon.core.utils import CheckHasPermission
from django.contrib.auth.mixins import LoginRequiredMixin
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from rest_framework.authentication import BasicAuthentication

from fiscallizeon.exams.serializers.randomizations import RandomizationVersionSerializer 

class RandomizationViewSet(LoginRequiredMixin, CheckHasPermission, viewsets.ModelViewSet):
    serializer_class = RandomizationVersionSerializer
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    authentication_classes = (CsrfExemptSessionAuthentication, )
    queryset = RandomizationVersion.objects.all()