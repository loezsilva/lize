from django.db.models import Q

from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView

from fiscallizeon.core.paginations import LimitOffsetPagination

from ..models import Competence
from ..serializers2.competence import CompetenceSerializer


@extend_schema(tags=['Competências'])
class CompetenceListView(ListAPIView):
    serializer_class = CompetenceSerializer
    pagination_class = LimitOffsetPagination
    required_scopes = ['read', 'write']

    def get_queryset(self):
        queryset = Competence.objects.filter(
            Q(client__in=self.request.user.get_clients_cache()) | Q(client__isnull=True),
        ).values()

        return queryset
