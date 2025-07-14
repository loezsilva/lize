from django.conf import settings
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.core.utils import CheckHasPermission
from rest_framework.authentication import BasicAuthentication
from fiscallizeon.integrations.apis.subjects.serializers import SubjectCodeSerializer
from fiscallizeon.integrations.models import SubjectCode


class SubjectCodeListCreateAPIView(ListCreateAPIView):
    serializer_class = SubjectCodeSerializer
    required_permissions = [settings.COORDINATION]
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    def get_queryset(self):
        return SubjectCode.objects.filter(client__in=self.request.user.get_clients_cache())

class SubjectCodeRetrieveUpdateDestroyAPIView(CheckHasPermission, RetrieveUpdateDestroyAPIView):
    queryset = SubjectCode.objects.all()
    serializer_class = SubjectCodeSerializer
    required_permissions = [settings.COORDINATION]
    authentication_classes = (CsrfExemptSessionAuthentication, )


api_subject_code_list_create = SubjectCodeListCreateAPIView.as_view()
api_subject_code_retrieve_update_destroy = SubjectCodeRetrieveUpdateDestroyAPIView.as_view()


