
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework import generics
from rest_framework.response import Response
from fiscallizeon.clients.models import Client
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.subjects.serializers.subjects import SubjectSimpleSerializer
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.inspectors.models import Inspector, TeacherSubject
from fiscallizeon.subjects.models import Subject
class SubjectsCreateApiView(LoginRequiredMixin, CheckHasPermission, generics.CreateAPIView):
    required_permissions = [settings.COORDINATION, settings.INSPECTOR, settings.TEACHER]
    serializer_class = SubjectSimpleSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def perform_create(self, serializer):
        data = serializer.validated_data
        serializer.validated_data['knowledge_area'] = data['parent_subject'].knowledge_area
        serializer.validated_data['client'] = Client.objects.get(pk=self.request.user.get_clients_cache()[0])
        serializer.validated_data['created_by'] = self.request.user

        
        return super().perform_create(serializer)


class InspectorSubjectsView(generics.GenericAPIView):
    serializer_class = SubjectSimpleSerializer

    def get(self, request, *args, **kwargs):
        inspector_id = kwargs.get('pk')

        try:
            inspector = Inspector.objects.get(pk=inspector_id)

        except Inspector.DoesNotExist:
            return Response({"detail": "Inspector not found."}, status=404)
        subjects = Subject.objects.filter(teachersubject__teacher=inspector)
        serializer = self.get_serializer(subjects, many=True)
        return Response(serializer.data)