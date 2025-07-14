from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView

from fiscallizeon.clients.models import Unity
from fiscallizeon.clients.serializers2.unity import UnitySerializer
from fiscallizeon.core.paginations import LimitOffsetPagination


@extend_schema(tags=['Unidades'])
class UnityListView(ListAPIView):
    serializer_class = UnitySerializer
    pagination_class = LimitOffsetPagination
    required_scopes = ['read', 'write']

    def get_queryset(self):
        return Unity.objects.filter(
            client__in=self.request.user.get_clients()
        )