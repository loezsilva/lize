import moment

from decimal import Decimal
from datetime import datetime, time, timedelta
from django.db.models.aggregates import Avg, Count
from django.db.models.expressions import OuterRef, Subquery
from django.template.defaultfilters import safe
from django.db.models.query_utils import Q
from django.db.models import DecimalField
from django.db.models.functions import Cast, Coalesce
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.pagination import LimitOffsetPagination

from rest_framework.generics import ListAPIView
from rest_framework.renderers import JSONRenderer
from rest_framework.authentication import BasicAuthentication
from chartjs.views.lines import BaseLineChartView


from fiscallizeon.questions.models import Question
from fiscallizeon.applications.api import application
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.analytics.api.analytic import get_applications
from fiscallizeon.analytics.models import ApplicationStudentLevelQuestion, ClassSubjectApplicationLevel
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.analytics.api.serializers.charts_serializers import CoordinationApplicationsSerializer

from sql_util.utils import SubqueryCount, SubqueryAggregate

class CoordinationChartApplicationsListAPIView(LoginRequiredMixin, CheckHasPermission, ListAPIView):
    renderer_classes = [JSONRenderer]
    required_permissions = ['coordination']
    serializer_class = CoordinationApplicationsSerializer
    queryset = Application.objects.none()
    authentication_classes = (CsrfExemptSessionAuthentication, )
    pagination_class = LimitOffsetPagination
    page_size = 50

    def dispatch(self, request):
        request.GET._mutable = True
        if not request.GET.get("limit", None):
            request.GET["limit"] = 30

        if not request.GET.get("offset", None):
            request.GET["offset"] = 0

        request.GET._mutable = False

        return super(CoordinationChartApplicationsListAPIView, self).dispatch(request)
        
    
    def get_queryset(self):
        return get_applications(self.request)

class CoordinationChartApplicationsSummaryChartView(LoginRequiredMixin, CheckHasPermission, BaseLineChartView):
    required_permissions = ['coordination']
    authentication_classes = (CsrfExemptSessionAuthentication, )
    queryset = Application.objects.none
    presence_percent = 0
    pauses_average_duration_applications = []
    average_duration_applications = []

    def dispatch(self, request):
        
        self.queryset = get_applications(request)

        # Arrays necessários para os calculos
        total_students_in_applications = []
        total_finish_students = []
        self.pauses_average_duration_applications = []
        self.average_duration_applications = []
        
        for application in self.queryset:
            total_students_in_applications.append(application.students.count())
            
            total_finish_students.append(application.students.count() - application.finish_students_count())

        # Transforma o resultado em porcentagem
        if sum(total_students_in_applications) > 0:
            self.presence_percent = ((sum(total_students_in_applications) - sum(total_finish_students)) / sum(total_students_in_applications)) * 100

        else:
            self.presence_percent = ((sum(total_students_in_applications) - sum(total_finish_students)) / 1) * 100

        
        return super(CoordinationChartApplicationsSummaryChartView, self).dispatch(request)

    def get_context_data(self, **kwargs):
        context = super(CoordinationChartApplicationsSummaryChartView, self).get_context_data(**kwargs)
        context.update(
            {
                "datasets": self.get_datasets(),
                "labels": self.get_labels(),
                "presence_percent": self.presence_percent,
            }
        )
        return context

    def get_labels(self):
        labels = []
        return labels

    def get_providers(self):
        return []

    def get_data(self):
        return [[self.presence_percent, 100 - self.presence_percent]]



coordination_applications_list = CoordinationChartApplicationsListAPIView.as_view()
coordination_chart_applications_summary = CoordinationChartApplicationsSummaryChartView.as_view()