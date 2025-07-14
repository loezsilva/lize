from rest_framework import generics
from django.conf import settings
from fiscallizeon.applications.models import Annotation
from fiscallizeon.applications.serializers.annotation import AnnotationSerializer, ApplicationAnnotationSerializer
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.core.api import CsrfExemptSessionAuthentication

from rest_framework.authentication import BasicAuthentication 

from django.contrib.auth.mixins import LoginRequiredMixin


class AnnotationCreate(LoginRequiredMixin, CheckHasPermission, generics.CreateAPIView):
    required_permissions = [settings.COORDINATION, settings.INSPECTOR, settings.TEACHER, ]
    serializer_class = AnnotationSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def perform_create(self, serializer):
        serializer.save(
            inspector=self.request.user,
        )

class ApplicationAnnotationCreate(LoginRequiredMixin, CheckHasPermission, generics.CreateAPIView):
    required_permissions = [settings.COORDINATION, settings.INSPECTOR, settings.TEACHER, ]
    serializer_class = ApplicationAnnotationSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def perform_create(self, serializer):
        serializer.save(
            inspector=self.request.user,
        )
        

annotation_create_api = AnnotationCreate.as_view()
application_annotation_create_api = ApplicationAnnotationCreate.as_view()
