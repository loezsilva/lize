from django.conf import settings
from rest_framework import generics
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.core.api import CsrfExemptSessionAuthentication

from fiscallizeon.corrections.models import CorrectionTextualAnswer, CorrectionFileAnswer
from fiscallizeon.corrections.serializers.correction import (
    CorrectionTextualAnswerSerializer, 
    CorrectionFileAnswerSerializer, 
    CorrectionFileAnsweOrderSerializer, 
    CorrectionTextualAnswerOrderSerializer, 
    TextCorrectionSerializer,
    DeviationSerializer,
)
from ..models import TextCorrection, CorrectionCriterion, CorrectionDeviation
from fiscallizeon.core.utils import SimpleAPIPagination, CheckHasPermissionAPI
from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from djangorestframework_camel_case.parser import CamelCaseJSONParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer

class TextCorrectionViewSet(CheckHasPermissionAPI, viewsets.ModelViewSet):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    serializer_class = TextCorrectionSerializer
    queryset = TextCorrection.objects.all()
    pagination_class = SimpleAPIPagination
    authentication_classes = (CsrfExemptSessionAuthentication,)
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        queryset = queryset.filter(
            Q(client__isnull=True) |
            Q(client=user.client)
        )
        
        return queryset
    
    @action(detail=False, methods=["GET"])
    def deviations(self, request, pk=None):
        criterion = self.request.GET.get('criterion')
        search = self.request.GET.get('search')
        
        deviations = CorrectionDeviation.objects.filter(
            Q(criterion=criterion),
            Q(
                Q(short_name__icontains=search) |
                Q(description__icontains=search)
            )
        )
        
        return Response(DeviationSerializer(instance=deviations, many=True).data)

#TextualAnswer
class CorrectionTextualAnswerListCreateAPIView(LoginRequiredMixin, CheckHasPermission, generics.ListCreateAPIView):
    serializer_class = CorrectionTextualAnswerSerializer
    queryset = CorrectionTextualAnswer.objects.all()
    required_permissions = [settings.TEACHER, settings.COORDINATION]
    authentication_classes = (CsrfExemptSessionAuthentication, )

class CorrectionTextualAnswerRetrieveUpdateAPIView(LoginRequiredMixin, CheckHasPermission, generics.RetrieveUpdateAPIView):
    serializer_class = CorrectionTextualAnswerSerializer
    queryset = CorrectionTextualAnswer.objects.all()
    required_permissions = [settings.TEACHER, settings.COORDINATION]
    authentication_classes = (CsrfExemptSessionAuthentication, )
#FileAnswer
class CorrectionFileAnswerListCreateAPIView(LoginRequiredMixin, CheckHasPermission, generics.ListCreateAPIView):
    serializer_class = CorrectionFileAnswerSerializer
    queryset = CorrectionFileAnswer.objects.all()
    required_permissions = [settings.TEACHER, settings.COORDINATION]
    authentication_classes = (CsrfExemptSessionAuthentication, )

class CorrectionFileAnswerRetrieveUpdateAPIView(LoginRequiredMixin, CheckHasPermission, generics.RetrieveUpdateAPIView):
    serializer_class = CorrectionFileAnswerSerializer
    queryset = CorrectionFileAnswer.objects.all()
    required_permissions = [settings.TEACHER, settings.COORDINATION]
    authentication_classes = (CsrfExemptSessionAuthentication, )

class CorrectionTextualCriterionAPIListView(LoginRequiredMixin, CheckHasPermission, generics.ListAPIView):
    serializer_class = CorrectionTextualAnswerOrderSerializer
    required_permissions = [settings.TEACHER, settings.COORDINATION]
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def get_queryset(self):
        text_correction = self.request.query_params.get('text_correction', None)
        application_student_id = self.request.query_params.get('application_student_id', None)

        if application_student_id:
            return CorrectionTextualAnswer.objects.filter(
                textual_answer__student_application__id=application_student_id,
                correction_criterion__text_correction__id=text_correction,
            )
        return CorrectionTextualAnswer.objects.none()
    
class CorrectionFileCriterionAPIListView(LoginRequiredMixin, CheckHasPermission, generics.ListAPIView):
    serializer_class = CorrectionFileAnsweOrderSerializer
    required_permissions = [settings.TEACHER, settings.COORDINATION]
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def get_queryset(self):
        text_correction = self.request.query_params.get('text_correction', None)
        application_student_id = self.request.query_params.get('application_student_id', None)

        if application_student_id:
            return CorrectionFileAnswer.objects.filter(
                file_answer__student_application__id=application_student_id,
                correction_criterion__text_correction__id=text_correction,
            )
        return CorrectionFileAnswer.objects.none()