from django.db.models import Q

from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView

from fiscallizeon.core.paginations import LimitOffsetPagination

from ..models import BaseText
from ..serializers2.base_text import BaseTextSerializer


@extend_schema(tags=['Textos base'])
class BaseTextListView(ListAPIView):
    serializer_class = BaseTextSerializer
    pagination_class = LimitOffsetPagination
    required_scopes = ['read', 'write']

    def get_queryset(self):
        queryset = BaseText.objects.filter(
            question__coordinations__unity__client__in=self.request.user.get_clients_cache(),
        ).distinct()

        return queryset
