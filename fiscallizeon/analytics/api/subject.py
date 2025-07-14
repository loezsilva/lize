import random
from decimal import Decimal

from django.db.models.expressions import OuterRef, Subquery

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Q, Value, Count, Avg, DecimalField
from django.db.models.functions import Coalesce, Cast


from rest_framework.generics import ListAPIView
from rest_framework.renderers import JSONRenderer
from rest_framework.authentication import BasicAuthentication

from chartjs.views.lines import BaseLineChartView

from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.subjects.models import KnowledgeArea, Subject
from fiscallizeon.analytics.api.analytic import get_applications
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.analytics.api.serializers.charts_serializers import CoordinationSubjectsSerializer
from fiscallizeon.analytics.models import ApplicationStudentLevelQuestion, ClassSubjectApplicationLevel

from sql_util.utils import SubqueryCount, SubqueryAggregate


class CoordinationChartAreaPerformanceChartView(LoginRequiredMixin, CheckHasPermission, BaseLineChartView):
    required_permissions = ['coordination']
    authentication_classes = (CsrfExemptSessionAuthentication, )
    applications = Application.objects.all()
    knowledge_area_ids = []
    knowledge_areas = KnowledgeArea.objects.none()

    def dispatch(self, request):
        self.applications = get_applications(request)
        self.knowledge_area_ids = list(
            set(
                self.applications.filter(
                    exam__examteachersubject__teacher_subject__subject__knowledge_area__isnull=False
                ).values_list(
                    "exam__examteachersubject__teacher_subject__subject__knowledge_area__pk", flat=True)
                )
            )

        self.knowledge_areas = KnowledgeArea.objects.filter(
            pk__in=self.knowledge_area_ids,
        ).distinct().order_by('name')

        for knowledge_area in self.knowledge_areas:
            knowledge_area.performance = ClassSubjectApplicationLevel.objects.filter(
                teacher_subject__subject__knowledge_area=knowledge_area
            ).get_performance(
                request=self.request
            )
            
        
        return super(CoordinationChartAreaPerformanceChartView, self).dispatch(request)

    def get_dataset_options(self, index, color):
        default_opt = {
            'maxBarThickness': 40
        }
        return default_opt

    def get_labels(self):
        labels = []

        for knowledge_area in self.knowledge_areas:
            if knowledge_area.performance and knowledge_area.performance > 0:
                labels.append(knowledge_area.name)

        return labels

    def get_providers(self):
        return []

    def get_data(self):
        values = []

        for knowledge_area in self.knowledge_areas:
            if knowledge_area.performance and knowledge_area.performance > 0:
                values.append(knowledge_area.performance)

        return [values]

class CoordinationListSubjectsListAPIView(LoginRequiredMixin, CheckHasPermission, ListAPIView):

    renderer_classes = [JSONRenderer]
    required_permissions = ['coordination']
    serializer_class = CoordinationSubjectsSerializer
    queryset = Subject.objects.none()
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    def get_queryset(self):        
        applications = list(get_applications(self.request))
        
        self.queryset = Subject.objects.filter(
           teachersubject__examteachersubject__exam__application__in=applications
        ).distinct()
        
        subjects_list = []
        
        for subject in self.queryset:
            subject.performance_total = ClassSubjectApplicationLevel.objects.filter(
                teacher_subject__subject=subject
            ).get_performance(
                request=self.request
            )

            if subject.performance_total and subject.performance_total > 0:
                subjects_list.append(subject)
        
        return subjects_list


coordination_chart_areas_performance = CoordinationChartAreaPerformanceChartView.as_view()
coordination_list_subjects = CoordinationListSubjectsListAPIView.as_view()