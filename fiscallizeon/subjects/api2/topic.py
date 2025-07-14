from django.db.models import F, Case, When, Value, CharField
from django.db.models.functions import Concat

from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView

from fiscallizeon.core.paginations import LimitOffsetPagination

from ..models import Topic
from ..serializers2.topic import TopicSerializer


@extend_schema(tags=['Tópicos (assuntos abordados)'])
class TopicListView(ListAPIView):
    serializer_class = TopicSerializer
    pagination_class = LimitOffsetPagination
    required_scopes = ['read', 'write']

    def get_queryset(self):
        queryset = Topic.objects.filter(
            question__coordinations__unity__client__in=self.request.user.get_clients_cache(),
        ).annotate(
            creator=F('created_by'),
            stage_description=Case(
                When(stage=1, then=Value('1ª etapa')),
                When(stage=2, then=Value('2ª etapa')),
                When(stage=3, then=Value('3ª etapa')),
                When(stage=4, then=Value('4ª etapa')),
                When(stage=5, then=Value('5ª etapa')),
                When(stage=6, then=Value('6ª etapa')),
                default=Value('Geral')
            ),
            grade_name=Case(
                When(grade__level=0, then=Concat(Value('Ensino médio - '), F('grade__name'), Value('ª série'))),
                When(grade__level=1, then=Concat(Value('Ensino fundamental - '), F('grade__name'), Value('º ano'))),
                default=Value('Indefinido'),
            ),
        ).distinct().values()

        return queryset
