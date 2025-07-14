from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView

from django.db.models import Q

from fiscallizeon.subjects.models import Subject
from fiscallizeon.subjects.serializers2.subject import SubjectSimpleSerializer
from fiscallizeon.core.paginations import LimitOffsetPagination


@extend_schema(tags=['Disciplinas'])
class SubjectListView(ListAPIView):
    serializer_class = SubjectSimpleSerializer
    pagination_class = LimitOffsetPagination
    required_scopes = ['read', 'write']

    def get_queryset(self):
        queryset = self.request.user.get_availables_subjects()
        return queryset