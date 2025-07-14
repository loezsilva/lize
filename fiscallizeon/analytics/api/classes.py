import random
from decimal import Decimal
from rest_framework.authentication import BasicAuthentication
from chartjs.views.lines import BaseLineChartView

from django.db.models.expressions import OuterRef, Subquery
from django.db.models import Count, Sum, Q, Avg, F, When, Value, Case, query
from django.contrib.auth.mixins import LoginRequiredMixin

from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.analytics.api.analytic import get_applications
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.analytics.models import ApplicationStudentLevelQuestion, ClassSubjectApplicationLevel

from sql_util.utils import SubqueryAggregate


class CoordinationChartClassesSummaryChartView(LoginRequiredMixin, CheckHasPermission, BaseLineChartView):
    required_permissions = ['coordination']
    authentication_classes = (CsrfExemptSessionAuthentication, )
    queryset = SchoolClass.objects.all()
    classes = []
    
    def dispatch(self, request):
        applications = list(get_applications(request))
        user = self.request.user
        if user.is_authenticated:
            self.queryset = SchoolClass.objects.filter(
                coordination__in=user.get_coordinations_cache(),
                students__applicationstudent__application__in=applications
            ).order_by("name").distinct()

            if self.request.GET.getlist("q_classes"):
                self.queryset = self.queryset.filter(
                    pk__in=self.request.GET.getlist("q_classes")
                )

            self.classes = []

            for classe in self.queryset:
                classe.performance = ClassSubjectApplicationLevel.objects.filter(
                    school_class=classe,
                ).get_performance(
                    request=request
                )
            
            for classe in self.queryset:
                self.classes.append({
                    "name": f'{classe.name} - {classe.coordination.unity.name}',
                    "performance": classe.performance
                })

        return super(CoordinationChartClassesSummaryChartView, self).dispatch(request)
    
    def get_context_data(self, **kwargs):
        context = super(CoordinationChartClassesSummaryChartView, self).get_context_data(**kwargs)
        
        classes = []
        for classe in self.queryset:
            classe_dict = {
                "name": classe.name,
                "students": []
            }

            classes.append(classe)

        context.update(
            {
                "classes": classes,
                "students_count": self.queryset.aggregate(total = Count('students')).get('total', 0)
            }
        )
        
        return context

    def get_labels(self):
        names_classes = []
        for classe in self.classes:
            if classe['name'] != None and not classe['name'] in names_classes and classe['performance'] and classe['performance'] > 0:
                names_classes.append(classe['name'])

        return names_classes

    def get_providers(self):
        return []

    def get_data(self):
        values = []
        names_classes = []

        for classe in self.classes:
            if classe['name'] != None and not classe['name'] in names_classes and classe['performance'] and classe['performance'] > 0:
                names_classes.append(classe['name'])
                values.append(classe['performance'])

        return [values]



coordination_chart_classes_summary = CoordinationChartClassesSummaryChartView.as_view()