import django_filters
from django.db.models import F, Case, When, Value

from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView

from fiscallizeon.core.paginations import LimitOffsetPagination
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend

from ..models import Exam
from ..serializers2.exam import ExamSerializer

class ExamFilter(django_filters.FilterSet):
    created_at_year = django_filters.NumberFilter(field_name='created_at', lookup_expr='year')

    class Meta:
        model = Exam
        fields = ['created_at_year', 'teaching_stage', 'education_system']

@extend_schema(tags=['Cadernos de prova'])
class ExamListView(ListAPIView):
    serializer_class = ExamSerializer
    pagination_class = LimitOffsetPagination
    filter_backends = [SearchFilter, DjangoFilterBackend]
    required_scopes = ['read', 'write']
    search_fields = ['id', 'name', 'teaching_stage__name', 'education_system__name']
    filterset_class = ExamFilter
    ordering_fields = ['name', 'created_at', ]

    def get_queryset(self):
        queryset = Exam.objects.prefetch_related('coordinations').filter(
            coordinations__unity__client__in=self.request.user.get_clients_cache(),
            is_abstract=False,
        ).select_related('coordinations__unity', 'coordinations__unity__client').annotate(
            # creator=F('created_by__name'),
            # status_description=Case(
            #     When(status=0, then=Value('Elaborando')),
            #     When(status=1, then=Value('Revisão de itens')),
            #     When(status=2, then=Value('Fechada')),
            #     When(status=3, then=Value('Diagramação')),
            #     default=Value('Não informado')
            # ),
            # category_description=Case(
            #     When(status=0, then=Value('Prova')),
            #     When(status=1, then=Value('Lista de Exercício')),
            #     default=Value('Não informado')
            # ),
            stage_id_erp=F('teaching_stage__code_export'),
        ).distinct().values()

        return queryset
