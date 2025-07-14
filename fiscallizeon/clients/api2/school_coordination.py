from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView

from fiscallizeon.clients.serializers2.school_coordination import SchoolCoordinationSerializer
from fiscallizeon.core.paginations import LimitOffsetPagination
from fiscallizeon.clients.models import SchoolCoordination

@extend_schema(tags=['Coordenações'])
class SchoolCoordinationListView(ListAPIView):
    serializer_class = SchoolCoordinationSerializer
    pagination_class = LimitOffsetPagination
    required_scopes = ['read', 'write']

    def get_queryset(self):
        return SchoolCoordination.objects.filter(
            unity__client__in=self.request.user.get_clients_cache()
        )