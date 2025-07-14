from rest_framework.generics import CreateAPIView, RetrieveAPIView
from rest_framework.authentication import BasicAuthentication 
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin

from fiscallizeon.events.serializers.question_error_report import QuestionErrorReportSerializer
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.core.api import CsrfExemptSessionAuthentication


class QuestionErrorReportCreateView(LoginRequiredMixin, CheckHasPermission, CreateAPIView):
    required_permissions = [settings.STUDENT, ]
    serializer_class = QuestionErrorReportSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def perform_create(self, serializer):
        serializer.save(
            sender=self.request.user,
        )

class QuestionErrorReportRetrieveView(LoginRequiredMixin, CheckHasPermission, RetrieveAPIView):
    required_permissions = [settings.COORDINATION, settings.INSPECTOR, settings.TEACHER, ]
    model = QuestionErrorReportSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )


question_error_report_create = QuestionErrorReportCreateView.as_view()
question_error_report_retrieve = QuestionErrorReportRetrieveView.as_view()