from django.db.models import F

from django.conf import settings

from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView, RetrieveAPIView

from fiscallizeon.core.paginations import LimitOffsetPagination
from fiscallizeon.core.utils import CheckHasPermissionAPI

from ..models import ExamTeacherSubject
from ..serializers2.exam_teacher_subject import ExamTeacherSubjectSerializer, ExamTeacherTeacherSubjectViewQuestionsSerializer


@extend_schema(tags=['Professores na prova'])
class ExamTeacherSubjectListView(ListAPIView):
    serializer_class = ExamTeacherSubjectSerializer
    pagination_class = LimitOffsetPagination
    required_scopes = ['read', 'write']

    def get_queryset(self):
        queryset = ExamTeacherSubject.objects.filter(
            exam__coordinations__unity__client__in=self.request.user.get_clients_cache(),
        ).annotate(
            teacher_id=F('teacher_subject__teacher'),
            subject_id=F('teacher_subject__subject')
        ).distinct().values()

        return queryset
    
class ExamTeacherSubjectRetrieveAPIView(RetrieveAPIView, CheckHasPermissionAPI):
    required_permissions = [settings.TEACHER]
    serializer_class = ExamTeacherTeacherSubjectViewQuestionsSerializer
    
    def get_queryset(self):
        queryset = ExamTeacherSubject.objects.filter(
            exam__coordinations__unity__client__in=self.request.user.get_clients_cache(),
        )
        return queryset.distinct()
