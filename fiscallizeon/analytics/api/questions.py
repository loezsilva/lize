from fiscallizeon.exams.models import ExamQuestion
import random

from django.db.models import Q, Sum, Count, Avg
from django.contrib.auth.mixins import LoginRequiredMixin

from rest_framework.authentication import BasicAuthentication

from chartjs.views.lines import BaseLineChartView

from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.questions.models import Question
from fiscallizeon.analytics.api.analytic import get_applications
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.analytics.models import ApplicationStudentLevelQuestion, ClassSubjectApplicationLevel

class CoordinationChartQuestionsSummaryChartView(LoginRequiredMixin, CheckHasPermission, BaseLineChartView):
    required_permissions = ['coordination']
    authentication_classes = (CsrfExemptSessionAuthentication, )
    queryset = Application.objects.none
    questions = None

    def dispatch(self, request):
        self.questions = Question.objects.filter(
            examquestion__exam__application__in=get_applications(request)
        ).aggregate(
            total_questions=Count('pk', distinct=True),
            questions_easy=Count('pk', distinct=True, filter=Q(level=Question.EASY)),
            questions_medium=Count('pk', distinct=True, filter=Q(level=Question.MEDIUM)),
            questions_hard=Count('pk', distinct=True, filter=Q(level=Question.HARD)),
            questions_undefined=Count('pk', distinct=True, filter=Q(level=Question.UNDEFINED))
        )


        return super(CoordinationChartQuestionsSummaryChartView, self).dispatch(request)

    def get_context_data(self, **kwargs):
        context = super(CoordinationChartQuestionsSummaryChartView, self).get_context_data(**kwargs)
        
        context.update(
            {
                "questions_count": self.questions.get("total_questions", 0), 
                "questions_easy":self.questions.get("questions_easy", 0),
                "questions_medium": self.questions.get("questions_medium", 0),
                "questions_hard": self.questions.get("questions_hard", 0),
                "questions_undefined": self.questions.get("questions_undefined", 0)
            }
        )
        
        return context

    def get_labels(self):
        
        labels = ['Fácil', 'Médio', 'Difícil', 'Indefinido']
        return labels

    def get_providers(self):
        return []

    def get_data(self):
        return [[
            self.questions.get("questions_easy", 0), 
            self.questions.get("questions_medium", 0),
            self.questions.get("questions_hard", 0),
            self.questions.get("questions_undefined", 0),

        ]]


class CoordinationChartQuestionsPerformanceChartView(LoginRequiredMixin, CheckHasPermission, BaseLineChartView):
    required_permissions = ['coordination']
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def dispatch(self, request):

        return super(CoordinationChartQuestionsPerformanceChartView, self).dispatch(request)

    def get_context_data(self, **kwargs):
        context = super(CoordinationChartQuestionsPerformanceChartView, self).get_context_data(**kwargs)
        context.update(
            {
                "datasets": self.get_datasets(),
                "labels": self.get_labels(),
            }
        )
        
        return context

    def get_labels(self):
        
        labels = ['Fácil', 'Médio', 'Difícil', 'Indefinido']
        return labels

    def get_providers(self):
        return []

    def get_data(self):
        values = []
        applications = list(get_applications(self.request))

        for n in dict(Question.LEVEL_CHOICES).keys():
            values.append(
                ClassSubjectApplicationLevel.objects.filter(
                    level=n,
                ).get_performance(
                    request=self.request
                ) 
            )

        return [values]


coordination_chart_questions_summary = CoordinationChartQuestionsSummaryChartView.as_view()
coordination_chart_questions_performance = CoordinationChartQuestionsPerformanceChartView.as_view()
