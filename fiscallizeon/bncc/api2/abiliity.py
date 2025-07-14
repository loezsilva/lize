from django.db.models import Q

from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView

from fiscallizeon.core.paginations import LimitOffsetPagination

from ..models import Abiliity
from ..serializers2.abiliity import AbiliitySerializer


@extend_schema(tags=['Habilidades'])
class AbiliityListView(ListAPIView):
    serializer_class = AbiliitySerializer
    pagination_class = LimitOffsetPagination
    required_scopes = ['read', 'write']

    def get_queryset(self):
        queryset = Abiliity.objects.filter(
            Q(client__in=self.request.user.get_clients_cache()) | Q(client__isnull=True),
        ).values()

        return queryset
