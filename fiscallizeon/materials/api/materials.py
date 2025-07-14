from django.conf import settings

from rest_framework.generics import RetrieveAPIView
from fiscallizeon.materials.models import StudyMaterial
from fiscallizeon.materials.serializer.materials import StudyMaterialSerializer

from fiscallizeon.core.utils import CheckHasPermission
from django.contrib.auth.mixins import LoginRequiredMixin

from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from rest_framework.authentication import BasicAuthentication 



class StudyMaterialRetrieveAPIView(LoginRequiredMixin, CheckHasPermission, RetrieveAPIView):

    required_permissions = [settings.COORDINATION, settings.TEACHER]
    serializer_class = StudyMaterialSerializer
    queryset = StudyMaterial.objects.all()
    authentication_classes = [CsrfExemptSessionAuthentication, ]

api_study_material_detail = StudyMaterialRetrieveAPIView.as_view()