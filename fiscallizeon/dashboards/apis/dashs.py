import logging
import polars as pl

from rest_framework import viewsets, views, status
from rest_framework.decorators import action
from rest_framework.response import Response
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from djangorestframework_camel_case.parser import CamelCaseJSONParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
# from ..models import Dashboard, DashboardChart
# from ..serializers.dashs import DashboardSerializer, DashboardChartSerializer
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q

logger = logging.getLogger()

"""
DATAFRAME_LOCATION = 'media/dashboards/dataframes'

class DashboardsViewSet(viewsets.ModelViewSet):
    serializer_class = DashboardSerializer
    # authentication_classes = (CsrfExemptSessionAuthentication,)
    queryset = Dashboard.objects.all()

    def get_queryset(self):
        user = self.request.user

        queryset = user.get_dashboards()

        return queryset
    
    @action(detail=True, methods=["GET"])
    def get_charts(self, request, pk=None):
        return Response(DashboardChartSerializer(instance=self.get_object().charts.all(), many=True).data)

    
class DashboardsChartViewSet(viewsets.ModelViewSet):
    serializer_class = DashboardChartSerializer
    # authentication_classes = (CsrfExemptSessionAuthentication,)
    queryset = DashboardChart.objects.all()

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        queryset = queryset.filter(dashboard__in=user.get_dashboards())

        return queryset
    
    # FOLLOWUP QUESTIONS
    @action(detail=False, methods=['get'])
    def get_cards_followup(self, request, pk=None):
        
        data = request.GET

        type = data.get("type")
        
        user = self.request.user
        
        client = user.client

        if type == 'questions':

            path = f'{DATAFRAME_LOCATION}/{str(client.id)}/followup-{type}.parquet'

            dataframe: pl.DataFrame = pl.scan_parquet(path)

            deadline_groups = dataframe.filter(pl.col('total_questions') < pl.col('total_solicitation')).group_by('elaboration_deadline').agg(
                pl.struct(
                    pl.col('exam_id').alias('id'), 
                    pl.col('name'), 
                    pl.col('total_questions').alias('questions'), 
                    pl.col('total_solicitation').alias('total'), 
                    (pl.col('total_solicitation') - pl.col('total_questions')).alias('awaiting'),
                ).filter(pl.col('total_questions') < pl.col('total_solicitation')).alias('exams').unique(),
                pl.struct(
                    pl.col('teacher_id').alias('id'), 
                    pl.col('teacher_name').alias('name'), 
                    pl.col('total_questions').alias('questions'), 
                    pl.col('total_solicitation').alias('total'),
                    (pl.col('total_solicitation') - pl.col('total_questions')).alias('awaiting'),
                ).filter(pl.col('total_questions') < pl.col('total_solicitation')).alias('teachers').unique(),
            ).with_columns(
                pl.col('exams').map_elements(lambda x: sum(item['awaiting'] for item in x), return_dtype=pl.Int64).alias('awaiting'),
                pl.col('exams').map_elements(lambda x: sum(item['questions'] for item in x), return_dtype=pl.Int64).alias('questions'),
                pl.col('exams').map_elements(lambda x: sum(item['total'] for item in x), return_dtype=pl.Int64).alias('total'),
                pl.col('elaboration_deadline').alias('deadline'),
            ).with_columns(
                (pl.col('questions') / pl.col('total') * 100).round(0).alias('performance'),
            ).sort(pl.col('elaboration_deadline')).select('deadline', 'total', 'questions', 'awaiting', 'performance', 'exams', 'teachers')

            data = deadline_groups.collect().to_dicts()

        elif type == 'uploads':

            path = f'{DATAFRAME_LOCATION}/{str(client.id)}/followup-{type}.parquet'

            dataframe: pl.DataFrame = pl.scan_parquet(path)

            deadline_groups = dataframe.group_by('elaboration_deadline').agg(
                pl.struct(
                    pl.col('exam_id').alias('id'), 
                    pl.col('name'),
                    pl.col('objectives'), 
                    pl.col('discursives'), 
                    (pl.col('objectives') + pl.col('discursives')).alias('awaiting'),
                ).alias('exams').unique(),
            ).with_columns(
                pl.col('exams').map_elements(lambda x: sum(item['objectives'] for item in x), return_dtype=pl.Int64).alias('objectives'),
                pl.col('exams').map_elements(lambda x: sum(item['discursives'] for item in x), return_dtype=pl.Int64).alias('discursives'),
                pl.col('exams').map_elements(lambda x: sum(item['objectives'] + item['discursives'] for item in x), return_dtype=pl.Int64).alias('awaiting'),
                pl.col('elaboration_deadline').alias('deadline'),
            ).sort(pl.col('elaboration_deadline')).select('deadline', 'exams', 'objectives', 'discursives', 'awaiting')

            data = deadline_groups.collect().to_dicts()

        return Response(data)
    
    @action(detail=False, methods=['get'])
    def get_deadline_summary(self, request, pk=None):
        data = request.GET

        deadline = request.GET.get('deadline')

        type = request.GET.get('type')
        
        user = self.request.user
        
        client = user.client

        path = f'{DATAFRAME_LOCATION}/{str(client.id)}/followup-questions.parquet'

        df = pl.scan_parquet(path).filter(pl.col('elaboration_deadline').cast(str) == deadline).group_by('unity_id', 'unity_name').agg(
            pl.struct(
                pl.col('exam_id').alias('id'), 
                pl.col('name'), 
                pl.col('total_questions').alias('questions'), 
                pl.col('total_solicitation').alias('total'), 
                (pl.col('total_solicitation') - pl.col('total_questions')).alias('awaiting')
            ).filter(pl.col('total_questions') < pl.col('total_solicitation')).alias('exams').unique(),
            pl.struct(
                pl.col('teacher_id').alias('id'), 
                pl.col('teacher_name').alias('name'), 
                pl.col('total_questions').alias('questions'), 
                pl.col('total_solicitation').alias('total'),
                (pl.col('total_solicitation') - pl.col('total_questions')).alias('awaiting'),
            ).filter(pl.col('total_questions') < pl.col('total_solicitation')).alias('teachers').unique(),
        ).with_columns(
            pl.col('unity_id').alias('id'),
            pl.col('unity_name').alias('name'),
        ).select('id', 'name', 'exams', 'teachers')

        data = df.collect().to_dicts()

        return Response(data)
    
    @action(detail=False, methods=['get'])
    def get_teacher_deadline_exams_summary(self, request, pk=None):
        data = request.GET

        deadline = request.GET.get('deadline')

        teacher_id = request.GET.get('teacher_id')
        
        user = self.request.user
        
        client = user.client

        path = f'{DATAFRAME_LOCATION}/{str(client.id)}/followup-questions.parquet'

        df = pl.scan_parquet(path).select('elaboration_deadline', 'teacher_id', 'exam_id', 'name', 'total_questions', 'total_solicitation').filter(
            pl.col('elaboration_deadline').cast(str) == deadline, 
            pl.col('teacher_id').cast(str) == teacher_id
        ).with_columns(
            pl.col('exam_id').alias('id'), 
            pl.col('name'), 
            pl.col('total_questions').alias('questions'), 
            pl.col('total_solicitation').alias('total'), 
            (pl.col('total_solicitation') - pl.col('total_questions')).alias('awaiting')
        ).filter(pl.col('awaiting') > 0).unique().select('id', 'name', 'questions', 'total', 'awaiting')

        data = df.collect().to_dicts()

        return Response(data)
    # END FOLLOWUP QUESTIONS
"""