import django_filters

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Case, When, Value, CharField
from django.db.models.functions import Cast
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView

from fiscallizeon.core.paginations import LimitOffsetPagination

from ..models import Application
from ..serializers2.application import ApplicationSerializer



class ApplicationFilterSet(django_filters.FilterSet):
    result_released = django_filters.BooleanFilter(method="result_released_method")
    year = django_filters.NumberFilter(field_name="date__year", lookup_expr="exact")

    def result_released_method(self, queryset, name, value):
        if value is None:
            return queryset

        if value:
            return queryset.filter(
                student_stats_permission_date__lte=timezone.localtime(timezone.now())
            ) 
        else:
            return queryset.exclude(
                student_stats_permission_date__lte=timezone.localtime(timezone.now())
            )

    class Meta:
        model = Application
        fields = ["exam", "result_released", "year"]



@extend_schema(tags=['Aplicações'])
class ApplicationListView(ListAPIView):
    serializer_class = ApplicationSerializer
    pagination_class = LimitOffsetPagination
    required_scopes = ['read', 'write']
    ordering_fields = ('date',)
    filterset_class = ApplicationFilterSet


    def get_queryset(self):
        queryset = Application.objects.filter(
          students__client=self.request.user.client,
        ).annotate(
            classes_ids=ArrayAgg(Cast('school_classes', output_field=CharField())),
            applicationstudents_ids=ArrayAgg(Cast('applicationstudent', output_field=CharField())),
            finish_date=Cast('date_end', output_field=CharField()),
            start_date=Cast('date', output_field=CharField()),
            start_time=Cast('start', output_field=CharField()),
            finish_time=Cast('end', output_field=CharField()),
            category_description=Case(
                When(category=2, then=Value('Online')),
                When(category=3, then=Value('Presencial')),
                When(category=4, then=Value('Lista de Exercício')),
                default=Value('Indefinido')
            )
        ).values()

        return queryset
