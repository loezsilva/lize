from datetime import timedelta
from django.conf import settings
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status
from django_filters.rest_framework import DjangoFilterBackend 
from rest_framework.viewsets import ModelViewSet
from rest_framework.generics import RetrieveAPIView, CreateAPIView
from fiscallizeon.answers.models import OptionAnswer
from fiscallizeon.bncc.models import Abiliity
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.authentication import BasicAuthentication
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.clients.models import Unity
from fiscallizeon.core.api.csrf_exempt_session import CsrfExemptSessionAuthentication
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.bncc.serializers.ability import AbilitySerializer, AbilityViewSetSerializer, AbilityCreateApiSerializer
from fiscallizeon.exams.models import Exam, ExamQuestion
from django.db.models import Count, F, Q, Sum, ExpressionWrapper, DateTimeField
from django.db.models.functions import Coalesce
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.clients.models import Client

class AbilityRetrieveAPIView(LoginRequiredMixin, CheckHasPermission, RetrieveAPIView):
    queryset = Abiliity.objects.all()
    serializer_class = AbilitySerializer
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        user = self.request.user
        coordinations = user.get_coordinations_cache()
        
        classes = SchoolClass.objects.filter(
            Q(coordination__in=coordinations),
            Q(pk__in=self.request.GET.get('classes').split(',')) if self.request.GET.get('classes') else Q()
        )
        unities = Unity.objects.filter(
            Q(coordinations__in=coordinations),
            Q(pk__in=self.request.GET.get('unities').split(',')) if self.request.GET.get('unities') else Q()
        )
        
        exam = Exam.objects.filter(id=request.GET.get('exam')).first()
        
        if exam and (classes or unities):
            data = {
                "classes": [],
                "unities": [],
            }
            if classes:
                for classe in classes:
                    data['classes'].append({
                        "id": classe.id,
                        "name": f"{classe.coordination.name} - {classe.name}",
                        "value": self.get_ability_summary(instance, exam, classe),
                    })
                
            if unities:
                for unity in unities:
                    data['unities'].append({
                        "id": unity.id,
                        "name": unity.name,
                        "value": self.get_ability_summary(instance, exam, None, unity),
                    })
                    
            return Response({
                "ability": serializer.data,
                "classes": data['classes'],
                "unities": data['unities'],
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.data)

    def get_ability_summary(self, ability, exam, school_class = None, unity = None):
        user = self.request.user
        coordinations = user.get_coordinations_cache()
        
        applications_student = exam.get_application_students_started(coordinations=coordinations).filter(
            application__exam__questions__abilities=ability
        ).distinct()
        
        if school_class:
            applications_student = applications_student.annotate(
                correct_objetive_answers=Count(F('option_answers'), filter=Q(
                    option_answers__question_option__question__abilities=ability,
                    option_answers__status=OptionAnswer.ACTIVE,
                    option_answers__question_option__is_correct=True,
                    option_answers__student_application__student__classes=school_class,
                ), distinct=True
                ),
                all_answers=Count('option_answers', filter=Q(
                    Q(option_answers__status=OptionAnswer.ACTIVE, option_answers__student_application__student__classes=school_class, option_answers__question_option__question__abilities=ability),
                    Q(
                        Q(option_answers__question_option__is_correct=True) |
                        Q(option_answers__question_option__is_correct=False)
                    )), distinct=True
                ),
            ).distinct()
            
        if unity:
            applications_student = applications_student.filter(
                student__classes__coordination__unity=unity
            ).annotate(
                correct_objetive_answers=Count(F('option_answers'), filter=Q(
                option_answers__question_option__question__abilities=ability,
                option_answers__status=OptionAnswer.ACTIVE,
                option_answers__question_option__is_correct=True,
                ), distinct=True
                ),
                all_answers=Count('option_answers', filter=Q(
                        Q(
                            option_answers__status=OptionAnswer.ACTIVE, 
                            option_answers__question_option__question__abilities=ability,
                        ),
                        Q(
                            Q(option_answers__question_option__is_correct=True) |
                            Q(option_answers__question_option__is_correct=False)
                        )
                    ), distinct=True
                ),
            ).distinct()
            
                
        applications_student_aggregates = applications_student.aggregate(
            total_correct_objetive_answers=Sum('correct_objetive_answers'),
            total=Coalesce(Sum('all_answers'), 0),
        )
        
        return (applications_student_aggregates.get('total_correct_objetive_answers') / applications_student_aggregates.get('total')) * 100 if applications_student_aggregates.get('total') > 0 else 0
    
class AbilityViewSet(LoginRequiredMixin, CheckHasPermission, ModelViewSet):
    queryset = Abiliity.objects.all()
    serializer_class = AbilityViewSetSerializer
    required_permissions = [settings.STUDENT]
    authentication_classes = (CsrfExemptSessionAuthentication, BasicAuthentication)
    
    def list(self, request, *args, **kwargs):
        user = self.request.user
        queryset = self.filter_queryset(self.get_queryset())
        
        if self.request and self.request.GET.get('get_performance'):
            if self.request.GET.get('subject'):
                queryset = queryset.filter(
                    performances__student__user=user,
                    performances__subject=self.request.GET.get('subject')
                ).distinct()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
class AbiliityCreateApiView(LoginRequiredMixin, CheckHasPermission, CreateAPIView):
    queryset = Abiliity.objects.all()
    serializer_class = AbilityCreateApiSerializer
    required_permissions = [settings.COORDINATION, settings.TEACHER]

    def perform_create(self, serializer):
        serializer.validated_data['client'] = Client.objects.get(pk=self.request.user.get_clients_cache()[0])
        serializer.validated_data['created_by'] = self.request.user
        instance = serializer.save()
        return instance
    
competence_create_api = AbiliityCreateApiView.as_view()