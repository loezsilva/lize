import logging
from decimal import Decimal
from statistics import fmean
from django.urls import reverse
from fiscallizeon.core.utils import SimpleAPIPagination, CheckHasPermissionAPI, round_half_up
from fiscallizeon.applications.serializers.application_student import ApplicationStudentPerformanceSerializer
from fiscallizeon.classes.serializers import ClassesPerformancesSerializer
from django.core.cache import cache
from django.core.exceptions import BadRequest

from django.conf import settings
from fiscallizeon.exams.utils import is_exam_name_unique
from rest_framework import generics
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.classes.models import Grade, SchoolClass
from fiscallizeon.clients.models import QuestionTag, SchoolCoordination, Unity
from fiscallizeon.core.utils import CheckHasPermission, round_half_up
from rest_framework.filters import SearchFilter
from django.contrib.auth.mixins import LoginRequiredMixin
from fiscallizeon.core.print_colors import *
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.views import APIView
from django.db.models import Sum, Count
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend 
from django.core.files.base import ContentFile
from urllib.parse import urljoin

from fiscallizeon.exams.serializers.exams import (
    ExamCoordinationSerializer,
    ExamOrientationSerializer, 
    ExamQuestionSerializer,
    ExamQuestionVerySimpleSerializer, 
    ExamSimpleSerializer, 
    ExamTeacherSerializer, 
    ExamTeacherSubjectCreateSimpleSerializer,
    ExamTeacherSubjectOpenedOrToReviewSerializer, 
    ExamTeacherSubjectSerializer,
    ExamTeacherSubjectSimpleSerializer, 
    ExamTeacherSubjectUpdateSimpleSerializer, 
    ExamTeacherTeacherSubjectSerializer,
    ExamTeacherSubjectExamElaborationSerializer,
    ExamToReviewSerializer,
    QuestionTagStatusQuestionSerializer,
    StatusQuestionSerializer,
    ExamSumWeightSerializer,
    ExamQuestionTeacherSerializer,
    ExamQuestionNumberSerializer,
    
)

from collections import OrderedDict

from fiscallizeon.exams.models import Exam, ExamOrientation, ExamQuestion, ExamTeacherSubject, QuestionTagStatusQuestion, StatusQuestion

from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination

from rest_framework.exceptions import PermissionDenied

from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.inspectors.models import TeacherSubject, Inspector

from django.contrib import messages
from fiscallizeon.materials.models import StudyMaterial
from fiscallizeon.materials.serializer.materials import StudyMaterialSimpleSerializer
from fiscallizeon.questions.models import Question
from fiscallizeon.bncc.utils import get_bncc

from django.db.models.deletion import ProtectedError
from django.db.models import Q, Value, UUIDField, F
from django.utils import timezone

from fiscallizeon.subjects.models import Subject
from fiscallizeon.clients.serializers.unities import UnityPerformanceSerializer

from fiscallizeon.questions.handle import handle_question_duplication

from djangorestframework_camel_case.parser import CamelCaseJSONParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer

from fiscallizeon.notifications.functions import get_and_create_notifications
from fiscallizeon.notifications.models import Notification

from ..models import ClientCustomPage, ExamHeader, ExamBackgroundImage

logger = logging.getLogger()

class ExamTeacherSubjectViewSet(CheckHasPermissionAPI, viewsets.ModelViewSet):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    serializer_class = ExamTeacherSubjectExamElaborationSerializer
    queryset = ExamTeacherSubject.objects.all()
    pagination_class = SimpleAPIPagination
    authentication_classes = (CsrfExemptSessionAuthentication,)
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        if user.is_freemium:
            queryset = queryset.filter(exam__in=user.get_exams())
        else:
            queryset = queryset.filter(
                Q(
                    Q(teacher_subject__teacher__coordinations__in=user.get_coordinations_cache()) |
                    Q(teacher_subject__teacher__user=user)
                )
            ).distinct()
        
        return queryset
    
    @action(detail=True, methods=["GET"], serializer_class=None)
    def can_add_examquestion(self, request, pk=None):
        instance = self.get_object()
        
        if instance.block_quantity_limit and instance.examquestion_set.availables(exclude_annuleds=True).count() >= instance.quantity:
        
            return Response(status=status.HTTP_401_UNAUTHORIZED)
        
        return Response(status=status.HTTP_200_OK)
    @action(detail=True, methods=["GET"])
    def examquestions_weights(self, request, pk=None):
        
        exam_teacher_subject = self.get_object()
        examquestions = exam_teacher_subject.examquestion_set.all()
        
        return Response(examquestions.values('id', 'weight'))
    

class ExamListView(LoginRequiredMixin, CheckHasPermission, ListAPIView):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    serializer_class = ExamSimpleSerializer
    filter_backends = [SearchFilter, DjangoFilterBackend]
    required_scopes = ['read', 'write']
    filterset_fields = {
        'created_at': ['year'],
        'id': ['in', 'exact'],
    }
    search_fields = ('name',)

    def get_queryset(self):
        user = self.request.user
        get_abstracts = True if self.request.GET.get('get_abstracts') == 'true' else False
        
        queryset = Exam.objects.filter(
            coordinations__unity__client__in=user.get_clients_cache(),
            not_applicable=False,
        )

        if not get_abstracts:
            queryset = queryset.filter(is_abstract=False)
        
        if user.user_type == settings.TEACHER:
            return queryset.filter(
                examteachersubject__teacher_subject__teacher__user=user
            ).distinct()

        if self.request.GET.get('year'):
            queryset = queryset.filter(
                created_at__year=self.request.GET.get('year'),
            )
        
        
        return queryset.distinct()

class ExamRetrieveAPIView(LoginRequiredMixin, CheckHasPermission, RetrieveAPIView):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    serializer_class = ExamSimpleSerializer
    model = Exam
    
    def get_queryset(self):
        user = self.request.user

        queryset = Exam.objects.filter(
            coordinations__unity__client__in=user.get_clients_cache()
        ).distinct()

        if user.user_type == settings.TEACHER:
            return queryset.filter(created_by=user)
        
        return queryset
    
class ExamHistograms(LoginRequiredMixin, CheckHasPermission, APIView):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    def generate_histogram(self, exam_pk, request=None, subject_pk=None, bncc_pk=None, student_name=None, school_classes=None, classe_pk=None, subjects=None):
        
        #Caso não seja passado nenhum parametro o retorno será o histograma completo dos applicationsstudent (Desempenho dos alunos no caderno)
        exam = Exam.objects.get(pk=exam_pk)
        
        # To passando Student por que um exam pode ter várias application_student de um mesmo aluno!
        classe = SchoolClass.objects.get(pk=classe_pk) if classe_pk else None
        subject = Subject.objects.get(pk=subject_pk) if subject_pk else None
        application_students_started = exam.get_application_students_started()

        if request:
            user = request.user
            coordinations = user.get_coordinations_cache()
            application_students_started = exam.get_application_students_started(coordinations=coordinations)
        
        applications_student = application_students_started.filter(
            Q(student__name__icontains=student_name) if student_name else Q(),
            Q(student__classes__in=school_classes) if school_classes else Q(),
        ).distinct()
        
        students_count = applications_student.count()
        
        performances = [0, 0, 0, 0, 0]
        histogram: object = {
            "data": [],
            "categories": ['0% - 20%', '21% - 40%', '41% - 60%', '61% - 80%', '81% - 100%']
        }
        
        if subject and classe:
            students_count = applications_student.filter(student__classes=classe).count()
            for application_student in applications_student.filter(student__classes=classe):
                student_performance = application_student.get_performance(subject=subject)
                if student_performance <= 20:
                    performances[0] = performances[0] + 1
                elif student_performance <= 40:
                    performances[1] = performances[1] + 1
                elif student_performance <= 60:
                    performances[2] = performances[2] + 1
                elif student_performance <= 80:
                    performances[3] = performances[3] + 1
                elif student_performance <= 100:
                    performances[4] = performances[4] + 1

            histogram['data'] = [(performances[0] / students_count) * 100 if students_count else 0, (performances[1] / students_count) * 100 if students_count else 0, (performances[2] / students_count) * 100 if students_count else 0, (performances[3] / students_count) * 100 if students_count else 0, (performances[4] / students_count) * 100 if students_count else 0]
            return histogram
        
        if subjects:
            subjects = Subject.objects.filter(pk__in=subjects)
            
            for application_student in applications_student:
                application_student_subjects_performance = []
                for subject in subjects:
                    application_student_subjects_performance.append(application_student.get_performance(subject=subject))
                
                student_performance = fmean(application_student_subjects_performance) if application_student_subjects_performance else 0
                
                if student_performance <= 20:
                    performances[0] = performances[0] + 1
                elif student_performance <= 40:
                    performances[1] = performances[1] + 1
                elif student_performance <= 60:
                    performances[2] = performances[2] + 1
                elif student_performance <= 80:
                    performances[3] = performances[3] + 1
                elif student_performance <= 100:
                    performances[4] = performances[4] + 1
        else:
            for application_student in applications_student.filter(Q(student__classes=classe) if classe else Q()):
                
                if subject or bncc_pk and not classe:
                    student_performance = application_student.get_performance(subject=subject, bncc_pk=bncc_pk)
                else:
                    student_performance = application_student.get_performance()
                    
                if student_performance <= 20:
                    performances[0] = performances[0] + 1
                elif student_performance <= 40:
                    performances[1] = performances[1] + 1
                elif student_performance <= 60:
                    performances[2] = performances[2] + 1
                elif student_performance <= 80:
                    performances[3] = performances[3] + 1
                elif student_performance <= 100:
                    performances[4] = performances[4] + 1

        histogram['data'] = [(performances[0] / students_count) * 100 if students_count else 0, (performances[1] / students_count) * 100 if students_count else 0, (performances[2] / students_count) * 100 if students_count else 0, (performances[3] / students_count) * 100 if students_count else 0, (performances[4] / students_count) * 100 if students_count else 0]
        return histogram
        
    
    def get(self, request, pk) -> Response:   
        return Response(self.generate_histogram(
                pk, 
                request,
                request.GET.get('subject_pk', None),
                request.GET.get('bncc_pk', None),
                request.GET.get('q_student_name', None),
                request.GET.getlist('q_school_classes', None),
                request.GET.getlist('q_subjects', None),
            ),
            status=status.HTTP_200_OK
        )

class ExamSubjectsPerformance(LoginRequiredMixin, CheckHasPermission, APIView):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    class PerformanceSerializer(serializers.Serializer):
        id = serializers.UUIDField()
        name = serializers.CharField(max_length=255)        
        performance = serializers.DecimalField(max_digits=5, decimal_places=2, coerce_to_string=False)
        histogram = serializers.JSONField()
        count = serializers.IntegerField()
        
    def get(self, request, pk):
        exam = Exam.objects.get(pk=pk)
        subject_pk = self.request.GET.get('subject_pk', None)
        q_subjects = self.request.GET.getlist('q_subjects', None)
        q_school_classes = self.request.GET.getlist('q_school_classes', None)
        user = self.request.user
        coordinations = user.get_coordinations_cache()
        
        if subject_pk:
            subject = Subject.objects.get(pk=subject_pk)
            applications_student = exam.get_application_students_started(coordinations=coordinations).filter(
                Q(student__classes__in=q_school_classes) if q_school_classes else Q()
            )
            students_performances = []
            for application_student in applications_student:
                student_serialized = self.PerformanceSerializer(data={
                    "id": application_student.id,
                    "name": application_student.student.name,
                    "performance": application_student.get_performance(subject=subject),
                    "histogram": "",
                    "count": 1, 
                })
                if student_serialized.is_valid():
                    students_performances.append(student_serialized.data)
                
            return Response(students_performances, status=status.HTTP_200_OK)
        else: 
            subjects = exam.get_or_generate_students_performances_subjects(coordinations=coordinations).filter(
                Q(
                    Q(subject__in=q_subjects) |
                    Q(teachersubject__subject__in=q_subjects)
                ) if q_subjects else Q()
            )
            
            subjects_summary = []
            for subject in subjects:
                subject_object = {
                    "id": subject.id,
                    "name": subject.__str__(),
                    "performance": 0,
                    "histogram": {
                        "categories": ['0% - 20%', '21% - 40%', '41% - 60%', '61% - 80%', '81% - 100%'],
                        "data": [],
                    },
                    "loads": {
                        "performances_loaded": False,
                        "students_performances_loaded": False,
                        "classes_performances_loaded": False,
                        "unities_performances_loaded": False,
                    },
                    "students_performances": [],
                    "classes_performances": [],
                    "unities_performances": [],
                }
                
                subject_performance = subject.last_performance(exam=exam)

                if q_school_classes:
                    for classe in SchoolClass.objects.filter(pk__in=q_school_classes, coordination__in=coordinations):
                        applications_student = ApplicationStudent.objects.filter(application__exam=exam, student__classes=classe)
                        students_performances = []
                        for application_student in applications_student:
                            students_performances.append(application_student.get_performance(subject=subject))
                        subject_object['performance'] = fmean(students_performances) if students_performances else 0
                else:
                    
                    subject_object['performance'] = subject_performance.first().performance if subject_performance else 0
                
                if subject_performance and subject_performance.first().histogram:
                    subject_object["histogram"]["data"] = subject_performance.first().histogram
                
                subjects_summary.append(subject_object)
            
            return Response(subjects_summary, status=status.HTTP_200_OK)
        
class SimplePagination(PageNumberPagination):
    page_size = 20
    display_page_controls = True
    page_size_query_param = 'page_size'
    
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('page_size', self.get_page_size(self.request)),
            ('count', self.page.paginator.count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))
    
class ApplicationStudentPerformance(LoginRequiredMixin, CheckHasPermission, ListAPIView):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    authentication_classes = (CsrfExemptSessionAuthentication, )
    serializer_class = ApplicationStudentPerformanceSerializer
    queryset = ApplicationStudent.objects.all()
    pagination_class = SimplePagination
    
    def get_queryset(self):
        queryset = super().get_queryset()
        subject_pk = self.request.GET.get('subject_pk', None)
        bncc_pk = self.request.GET.get('bncc_pk', None)
        exam_pk = self.request.GET.get('exam_pk', None)
        q_school_classes = self.request.GET.getlist('q_school_classes', None)
        user = self.request.user
        coordinations = user.get_coordinations_cache()

        if exam_pk and (subject_pk or bncc_pk):
            exam = Exam.objects.get(pk=exam_pk)
            queryset = exam.get_application_students_started(coordinations=coordinations).filter(
                Q(student__classes__in=q_school_classes) if q_school_classes else Q()
            )
        else:
            return queryset.none()
        
        queryset = queryset.annotate(
            subject_pk=Value(subject_pk if subject_pk else None, output_field=UUIDField()),
            bncc_pk=Value(bncc_pk if bncc_pk else None, output_field=UUIDField()),
        )
        return queryset.order_by('student__name')

class ClassesPerformances(LoginRequiredMixin, CheckHasPermission, ListAPIView):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    authentication_classes = (CsrfExemptSessionAuthentication, )
    serializer_class = ClassesPerformancesSerializer
    queryset = SchoolClass.objects.all()
    # pagination_class = SimplePagination
    
    def get_queryset(self):
        exam = Exam.objects.get(pk=self.kwargs['pk'])
        queryset = exam.get_classes().filter(
            Q(pk__in=self.request.GET.getlist('q_school_classes')) if self.request.GET.get('q_school_classes') else Q()
        ).filter(
            coordination__in=self.request.user.get_coordinations_cache()
        )
        subject_pk = self.request.GET.get('subject_pk', None)
        bncc_pk = self.request.GET.get('bncc_pk', None)
        
        if not (subject_pk or bncc_pk):
            return queryset.none()
        
        queryset = queryset.annotate(
            subject_pk=Value(subject_pk if subject_pk else None, output_field=UUIDField()),
            bncc_pk=Value(bncc_pk if bncc_pk else None, output_field=UUIDField()),
            exam_pk=Value(exam.pk, output_field=UUIDField()),
        )
        return queryset.order_by('name')
    
class ExamUnitiesPerformance(LoginRequiredMixin, CheckHasPermission, ListAPIView):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    authentication_classes = (CsrfExemptSessionAuthentication, )
    serializer_class = UnityPerformanceSerializer
    queryset = Unity.objects.all()
    
    def get_queryset(self):
        exam = Exam.objects.get(pk=self.kwargs['pk'])
        subject_pk = self.request.GET.get('subject_pk', None)
        bncc_pk = self.request.GET.get('bncc_pk', None)
        CACHE_KEY = f'exam-performance-unities-{str(exam.pk)}'
        CACHE_KEY += f'-{subject_pk}' if subject_pk else ''
        CACHE_KEY += f'-{bncc_pk}' if bncc_pk else ''

        print("----", CACHE_KEY)

        if not cache.get(CACHE_KEY):
            print("### NÃO TEM CACHE")
            user = self.request.user
            coordinations = user.get_coordinations_cache()       
            queryset = exam.get_unities().filter(
                Q(coordinations__in=coordinations),
                Q(pk__in=self.request.GET.getlist('q_unities')) if self.request.GET.get('q_unities') else Q()
            )
            
            if not (subject_pk or bncc_pk):
                return queryset.none()
            
            queryset = queryset.annotate(
                subject_pk=Value(subject_pk if subject_pk else None, output_field=UUIDField()),
                bncc_pk=Value(bncc_pk if bncc_pk else None, output_field=UUIDField()),
                exam_pk=Value(exam.pk, output_field=UUIDField()),
            )
            cache.set(CACHE_KEY, list(queryset.order_by('name')), 4 * 60 * 60)

        return cache.get(CACHE_KEY)
        
class ExamBnccPerformance(LoginRequiredMixin, CheckHasPermission, APIView):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    class PerformanceSerializer(serializers.Serializer):
        id = serializers.UUIDField()
        name = serializers.CharField(max_length=255)        
        performance = serializers.DecimalField(max_digits=5, decimal_places=2, coerce_to_string=False)
        histogram = serializers.JSONField()
        count = serializers.IntegerField()
    
    def get(self, request, pk):
        exam = Exam.objects.get(pk=pk)
        q_subjects = self.request.GET.getlist('q_subjects', None)
        q_school_classes = self.request.GET.getlist('q_school_classes', None)
        bncc_pk = self.request.GET.get('bncc_pk', None)
        only = self.request.GET.get('only', None)
        user = self.request.user
        coordinations = user.get_coordinations_cache()
        
        if bncc_pk:
            
            applications_student = exam.get_application_students_started(coordinations=coordinations).filter(
                Q(student__classes__in=q_school_classes) if q_school_classes else Q()
            )
            
            bncc = get_bncc(bncc_pk)
            
            students_performances = []
            
            for application_student in applications_student:
                student_serialized = self.PerformanceSerializer(data={
                    "id": application_student.id,
                    "name": application_student.student.name,
                    "performance": application_student.get_performance(bncc_pk=bncc.id),
                    "histogram": "",
                    "count": 1, 
                })
                if student_serialized.is_valid():
                    students_performances.append(student_serialized.data)
                    
            return Response(students_performances, status=status.HTTP_200_OK)
        
        else: 
            
            bnccs = exam.get_or_generate_students_performances_bnccs(coordinations=coordinations)
            
            topics = []
            if only == 'topics':
                bncc_topics = bnccs['topics'].filter(
                    Q(pk__in=exam.examquestion_set.availables(exclude_annuleds=True).values_list('question__topics')),
                    Q(subject__in=q_subjects) if q_subjects else Q()
                )
                for topic in bncc_topics:
                    
                    topic_performance = topic.last_performance(exam=exam)
                    
                    topic_object = {
                        "id": topic.id,
                        "name": topic.name,
                        "performance": topic_performance.first().performance if topic_performance else 0,
                        "histogram": {
                            "categories": ['0% - 20%', '21% - 40%', '41% - 60%', '61% - 80%', '81% - 100%'],
                            "data": topic_performance.first().histogram if topic_performance and topic_performance.first().histogram else [],
                        },
                        "loads": {
                            "performances_loaded": False,
                            "students_performances_loaded": False,
                            "classes_performances_loaded": False,
                            "unities_performances_loaded": False,
                        },
                        "students_performances": [],
                        "classes_performances": [],
                    }                            
                    topics.append(topic_object)
            
            abilities = []
            if only == 'abilities':
                bncc_abilities = bnccs['abilities'].filter(
                    Q(pk__in=exam.examquestion_set.availables(exclude_annuleds=True).values_list('question__abilities')),
                    Q(subject__in=q_subjects) if q_subjects else Q()
                )
                for ability in bncc_abilities:
                    ability_performance = ability.last_performance(exam=exam)
                    
                    ability_object = {
                        "id": ability.id,
                        "code": ability.code,
                        "text": ability.text,
                        "knowledge_object": ability.knowledge_object.text if ability.knowledge_object else '',
                        "performance": ability_performance.first().performance if ability_performance else 0,
                        "histogram": {
                            "categories": ['0% - 20%', '21% - 40%', '41% - 60%', '61% - 80%', '81% - 100%'],
                            "data": ability_performance.first().histogram if ability_performance and ability_performance.first().histogram else [],
                        },
                        "loads": {
                            "performances_loaded": False,
                            "students_performances_loaded": False,
                            "classes_performances_loaded": False,
                            "unities_performances_loaded": False,
                        },
                        "students_performances": [],
                        "classes_performances": [],
                    }
                    
                    abilities.append(ability_object)
                
            competences = []
            if only == 'competences':
                bncc_competences = bnccs['competences'].filter(
                    Q(pk__in=exam.examquestion_set.availables(exclude_annuleds=True).values_list('question__competences')),
                    Q(subject__in=q_subjects) if q_subjects else Q()
                )
                for competence in bncc_competences:
                    competence_performance = competence.last_performance(exam=exam)
                    
                    competence_object = {
                        "id": competence.id,
                        "code": competence.code,
                        "text": competence.text,
                        "code": competence.code,
                        "performance": competence_performance.first().performance if competence_performance else 0,
                        "histogram": {
                            "categories": ['0% - 20%', '21% - 40%', '41% - 60%', '61% - 80%', '81% - 100%'],
                            "data": competence_performance.first().histogram if competence_performance and competence_performance.first().histogram else [],
                        },
                        "loads": {
                            "performances_loaded": False,
                            "students_performances_loaded": False,
                            "classes_performances_loaded": False,
                            "unities_performances_loaded": False,
                        },
                        "students_performances": [],
                        "classes_performances": [],
                    }                    
                    competences.append(competence_object)
            
            return Response({
                "topics": topics,
                "abilities": abilities,
                "competences": competences,
            }, status=status.HTTP_200_OK)

class QuestionTagStatusQuestionCreate(LoginRequiredMixin, CheckHasPermission, generics.CreateAPIView):
    required_permissions = [settings.COORDINATION, settings.INSPECTOR, settings.TEACHER]
    serializer_class = QuestionTagStatusQuestionSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def perform_create(self, serializer):
        tags = self.request.data.get('tags', None)
        selected_tags = QuestionTag.objects.filter(pk__in=self.request.data.get('tags')) if tags else []
        serializer.save(
            status=StatusQuestion.objects.using('default').get(pk=self.kwargs.get('pk')),
            tags=selected_tags
        )

class QuestionTagStatusQuestionList(LoginRequiredMixin, CheckHasPermission, ListAPIView):
    required_permissions = [settings.COORDINATION, settings.INSPECTOR, settings.TEACHER]
    serializer_class = QuestionTagStatusQuestionSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def get_queryset(self):
        queryset = QuestionTag.objects.filter(pk=self.kwargs.get('pk'))

        return queryset

class StatusQuestionCreate(LoginRequiredMixin, CheckHasPermission, generics.CreateAPIView):
    required_permissions = [settings.COORDINATION, settings.INSPECTOR, settings.TEACHER]
    serializer_class = StatusQuestionSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def perform_create(self, serializer):
        give_score = self.request.data.get('give_score', False)
        distribute_in_exam_teacher_subject = self.request.data.get('distributeInExamTeacherSubject', False)
        question_fragment = self.request.data.get('question_fragment', '')
        source_status_question = self.request.data.get('source_status_question', None)

        serializer.save(
            exam_question=ExamQuestion.objects.using('default').get(pk=str(self.kwargs['pk'])),
            user=self.request.user,
            annuled_give_score=give_score,
            annuled_distribute_exam_teacher_subject=distribute_in_exam_teacher_subject,
            question_fragment=question_fragment,
            source_status_question=StatusQuestion.objects.get(pk=source_status_question) if source_status_question else None,
        )

class StatusQuestionUpdate(LoginRequiredMixin, CheckHasPermission, generics.UpdateAPIView):
    required_permissions = [settings.COORDINATION, settings.INSPECTOR, settings.TEACHER]
    serializer_class = StatusQuestionSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )
    queryset = StatusQuestion.objects.all()

    def perform_update(self, serializer):

        if serializer.instance.is_checked_by:
            serializer.instance.is_checked_by = None
        else:
            serializer.instance.is_checked_by = self.request.user
        
        serializer.save()

    def update(self, request, *args, **kwargs):

        instance = self.get_object()

        # Só quem pode dar o check nos vistos é um coordenador , ou o próprio professor que adicionou a questão
        # Só é possível remover o checked, o próprio usuário que adicionou o checked

        if instance.is_checked_by and instance.is_checked_by != self.request.user:
            return Response(
                {"detail": "Este status já foi verificado por outro usuário."},
                status=status.HTTP_403_FORBIDDEN,
            )
        
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )
        
class RevertStatusQuestionAPIView(LoginRequiredMixin, CheckHasPermission, APIView):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    def post(self, request):
        exam_question = request.data.get('exam_question')
        status_question = StatusQuestion.objects.filter(exam_question=exam_question, active=True).order_by('-created_at').first()
        tags = QuestionTagStatusQuestion.objects.filter(status=status_question)
        
        if status_question:
            status_question.delete()
            tags.delete()
            new_status = StatusQuestion.objects.filter(exam_question=exam_question).order_by('-created_at').first()
            if new_status:
                new_status.active = True
                new_status.save()
                return Response({"new_status": StatusQuestionSerializer(new_status).data}, status=status.HTTP_200_OK)

            return Response({"noLastStatus": True}, status=status.HTTP_200_OK)

        return Response(status=status.HTTP_404_NOT_FOUND)

class ExamTemplateListView(LoginRequiredMixin, CheckHasPermission, ListAPIView):
    required_permissions = [settings.COORDINATION]
    serializer_class = ExamSimpleSerializer
    filterset_fields = {
        'created_at': ['year'],
        'id': ['in', 'exact'],
    }
    search_fields = ('name',)

    def get_queryset(self):
        queryset = Exam.objects.filter(
            is_abstract=True,
            coordinations__unity__client__in=self.request.user.get_clients_cache(),
            not_applicable=False,
        ).distinct()

        return queryset
    
class ExamCoordinationAndTeacherViewSet(LoginRequiredMixin, CheckHasPermission, viewsets.ModelViewSet):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    serializer_class = ExamCoordinationSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )
    model = Exam

    def get_serializer_class(self):
        user = self.request.user
        if (self.request.method == 'POST' and user.user_type == settings.TEACHER) or (user.user_type == settings.TEACHER and not self.request.GET.get('is_discipline_coordinator')):
            return ExamTeacherSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        user = self.request.user
        queryset = Exam.objects.all().distinct()
        
        if user.user_type == settings.TEACHER:
            if user.inspector.is_discipline_coordinator:
                queryset = queryset.filter(
                    coordinations__in=user.get_coordinations_cache(),
                )
            else:
                queryset = queryset.filter(
                    coordinations__in=user.get_coordinations_cache(),
                    created_by=user
                )
        else:
            queryset = queryset.filter(
                coordinations__unity__client__in=user.get_clients_cache(),
            )

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # validação nome unico
        if not is_exam_name_unique(self.request.data.get('coordinations'), self.request.data.get('name')):
             return Response(f"Já existe um caderno com o nome '{self.request.data.get('name')}'", status=status.HTTP_400_BAD_REQUEST)
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        
        get_and_create_notifications(view=self, trigger=Notification.AFTER_CREATE)
        
        if self.request.data.get('add_materials'):
            return Response({"redirect_url": f"{reverse('exams:exams_update', kwargs={'pk': serializer.instance.pk})}?add_materials=true"}, status=status.HTTP_201_CREATED, headers=headers)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def perform_create(self, serializer):
        user = self.request.user
        selected_coordinations = SchoolCoordination.objects.none()
        if self.request.data.get('coordinations'):
            selected_coordinations = SchoolCoordination.objects.using('default').filter(pk__in=self.request.data.get('coordinations'))

        # NÃO REMOVER ESSA CONDIÇÃO, AQUI É DEFINIDO SE FOI O PROFESSOR OU A COORDENAÇÃO QUE CRIOU O CADERNO
        exam = None
        if user.user_type == settings.TEACHER:
            exam = serializer.save(
                coordinations=user.get_coordinations(),
                created_by=self.request.user,
                category=Exam.HOMEWORK,
            )
        else:
            exam = serializer.save(
                coordinations=selected_coordinations,
            )
        # FIM DA CONDIÇÃO
     
        base_url = self.request.build_absolute_uri('/') 
        teacher_subjects = self.request.data.get('teacher_subjects')
        for teacher_subject in teacher_subjects:
            teacher_subject['exam'] = serializer.instance.id

            try:
                if user.user_type == settings.TEACHER:
                    selected_teacher_subject = TeacherSubject.objects.using('default').get(teacher=self.request.user.inspector, subject=teacher_subject.get('subject'))
                    teacher_subject['teacher_subject'] = selected_teacher_subject.id
                else:
                    teacher_subject['grade'] = teacher_subject.get('grade').get('id')
                    teacher_subject['teacher_subject'] = teacher_subject.get('teacher_subject')

                biggest_order = serializer.instance.examteachersubject_set.using('default').all().order_by('-order').first()
                
                teacher_subject['order'] = (biggest_order.order + 1) if biggest_order else 0

                exam_teacher_subject_serialized = ExamTeacherSubjectCreateSimpleSerializer(data=teacher_subject)
                exam_teacher_subject_serialized.is_valid(raise_exception=True)
                exam_teacher_subject_serialized.save()    
                            
            except Exception as e:
                logger.exception(f"Erro ao criar e vincular exam_teacher_subject: {repr(e)}")

        if not exam.exam_print_config:
            client = self.request.user.get_clients().first()
            exam_print_config = client.get_exam_print_config()
            exam_print_config.pk = None
            exam_print_config.name = f'Configuração {exam.name}'

            exam_print_config_header = self.request.data.get('exam_print_config_header', None)
            if exam_print_config_header:
                exam_header = ExamHeader.objects.using('default').filter(
                    pk=exam_print_config_header,
                    user__coordination_member__coordination__unity__client__in=self.request.user.get_clients_cache(),
                ).last()
                if exam_header:
                    exam_print_config.header = exam_header
            else:
                exam_print_config.header = None

            exam_print_config.save()

            exam.exam_print_config = exam_print_config
            exam.save()

        if user.client_has_offset_answer_sheet:
            Exam.objects.generate_external_code(exam, user.get_clients().first())
        
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        total_grade = request.data.get('total_grade', None)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        if self.request.data.get('coordinations'):
            selected_coordinations = SchoolCoordination.objects.using('default').filter(pk__in=self.request.data.get('coordinations'))
            instance.coordinations.set(selected_coordinations)
        
        # validação nome unico
        if not is_exam_name_unique(self.request.data.get('coordinations'), self.request.data.get('name'), update=True, pk=self.request.data.get('id')):
             return Response(f"Já existe um caderno com o nome '{self.request.data.get('name')}'", status=status.HTTP_400_BAD_REQUEST)
        
        # Lógica acrescentada em 01/07/2025 para checar o valor mínimo que o caderno pode ter
        # Pois se tiver nota travada nos exam_teacher_subjects, o total_grade não poderá ser menor que a soma das notas dos exam_teacher_subjects
        if total_grade and float(total_grade) < instance.min_available_total_grade:
            return Response({
                "detail": f"O valor mínimo que o caderno pode ter é {instance.min_available_total_grade} que é a soma das notas travadas das solicitações."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        exam = serializer.save()

        exam_print_config_header = self.request.data.get('exam_print_config_header', None)
        if exam_print_config_header:
            exam_header = ExamHeader.objects.using('default').filter(
                pk=exam_print_config_header,
                user__coordination_member__coordination__unity__client__in=self.request.user.get_clients_cache(),
            ).last()
            if exam.exam_print_config and exam_header:
                exam.exam_print_config.header = exam_header
                exam.exam_print_config.save()
        else:
            if exam.exam_print_config:
                exam.exam_print_config.header = None
                exam.exam_print_config.save()

        if request.data.get("review", None):
            instance.status = Exam.SEND_REVIEW
            instance.save()

        get_and_create_notifications(view=self, trigger=Notification.AFTER_UPDATE)

        messages.success(self.request, 'Caderno atualizado com sucesso!')

        if self.request.GET.get('create_application'):
            return Response({ "data": serializer.data, "redirect_url": f"{reverse('applications:applications_create')}?exam={serializer.instance.id}"})

        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        instance = Exam.objects.using('default').annotate(
            user_pk=Value(self.request.user.pk, output_field=UUIDField())
        ).get(pk=kwargs['pk'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def perform_destroy(self, instance):
        instance.delete()
        
        get_and_create_notifications(view=self, trigger=Notification.AFTER_DELETE)
        
        messages.success(self.request, 'Caderno removido com sucesso!')
    
    @action(detail=True, methods=['get'])
    def subject_detail(self, request, pk=None):
        try:
            exam_teacher_subject = ExamTeacherSubject.objects.using('default').get(id=pk)
            serializer = ExamTeacherTeacherSubjectSerializer(exam_teacher_subject)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"O ExamTeacherSubject não existe: {repr(e)}")
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=False, methods=['get'])
    def get_orientations(self, request, pk=None):
        orientations = ExamOrientation.objects.filter(
            user__coordination_member__coordination__unity__client=self.request.user.client
        ).distinct()
        orientations_serializer = ExamOrientationSerializer(instance=orientations, many=True)
        return Response(orientations_serializer.data)

    @action(detail=True, methods=['post'])
    def create_exam_teacher_subject(self, request, pk=None):
        exam = self.get_object()

        teacher_subjects = request.data
        try:
            if not self.request.GET.get('multiple_subjects'):
                
                data = request.data.copy()
                    
                if not data.get('reviewed_by'):
                    data.pop('reviewed_by', None)

                if data['discursive_quantity'] and not isinstance(data['discursive_quantity'], int):
                    data['discursive_quantity'] = int(data['discursive_quantity'])
                elif not data['discursive_quantity']:
                    data['discursive_quantity'] = 0
                    
                if data['objective_quantity'] and not isinstance(data['objective_quantity'], int):
                    data['objective_quantity'] = int(data['objective_quantity'])
                elif not data['objective_quantity']:
                    data['objective_quantity'] = 0

                data['exam'] = exam.id
                
                biggest_order = exam.examteachersubject_set.using('default').all().order_by('-order').first()
                
                data['order'] = (biggest_order.order + 1) if biggest_order else 0
                
                exam_teacher_subject_serialized = ExamTeacherSubjectCreateSimpleSerializer(data=data)
                if ExamTeacherSubject.objects.using('default').filter(teacher_subject=request.data.get('teacher_subject'), exam=exam).exists() and not request.user.client_allow_same_teacher_subject:
                    return Response('O professor já foi adicionado anteriormente.', status=status.HTTP_409_CONFLICT)
                else:
                    if exam_teacher_subject_serialized.is_valid(raise_exception=True):
                        exam_teacher_subject_serialized.save()
                        return Response(ExamTeacherSubjectSerializer(exam_teacher_subject_serialized.instance).data, status=status.HTTP_200_OK)
                    else:
                        logger.exception(f"Erro no serializer: {repr(exam_teacher_subject_serialized.errors)}")
                        return Response("Ocorreu um erro, o professor não foi adicionado a esta prova", status=status.HTTP_400_BAD_REQUEST)

            else:

                exam_teacher_subjects_instances = []
                for _teacher_subject in teacher_subjects:
                    teacher_subject = TeacherSubject.objects.using('default').get(teacher=self.request.user.inspector, subject=_teacher_subject.get('subject'))
                    grade = Grade.objects.using('default').get(pk=_teacher_subject.get('grade'))
                    
                    biggest_order = exam.examteachersubject_set.using('default').all().order_by('-order').first()
                    
                    exam_teacher_subject = ExamTeacherSubject.objects.using('default').create(
                        teacher_subject=teacher_subject,
                        exam=exam,
                        grade=grade,
                        order=(biggest_order.order + 1) if biggest_order else 0,
                    )
                    exam_teacher_subjects_instances.append(exam_teacher_subject)

        except Exception as e:
            logger.exception(f"Erro ao criar e vincular exam_teacher_subject: {repr(e)}")
            return Response({ 
                "error": f"{repr(e)}",
                "message": f"Erro ao tentar criar e vincular a disciplina ao caderno"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(ExamTeacherTeacherSubjectSerializer(instance=exam_teacher_subjects_instances, many=True).data, status=status.HTTP_200_OK)
       
    @action(detail=True, methods=['post'])
    def delete_exam_teacher_subject(self, request, pk=None):
        try:
            exam_teacher_subject = ExamTeacherSubject.objects.using('default').get(id=pk)
            exam_teacher_subject.delete()
        except Exception as e:
            logger.error(f"Erro ao deletar exam_teacher_subject: {repr(e)}")
            logger.exception(f"Erro ao criar e remover exam_teacher_subject: {repr(e)}")
            return Response(status=status.HTTP_400_BAD_REQUEST)    
        return Response({"message": "Caderno Removido"}, status=status.HTTP_200_OK)
    


    @action(detail=True, methods=['put'])
    def update_exam_teacher_subject(self, request, pk=None):
        new_subject_id = request.data.get('subject_id', "")
        subdiscipline_id = request.data.get('subdiscipline_id', None)

        try:
            exam_teacher_subject_instance = ExamTeacherSubject.objects.using('default').get(pk=pk)
            exam_teacher_subject = ExamTeacherSubjectUpdateSimpleSerializer(
                instance=exam_teacher_subject_instance, 
                data=request.data
            )
            
            if exam_teacher_subject.is_valid(raise_exception=True):
                with transaction.atomic():
                    exam_teacher_subject.save()
                    
                    if new_subject_id and str(exam_teacher_subject_instance.teacher_subject.subject_id) != str(new_subject_id):
                        subject = Subject.objects.get(pk=new_subject_id)
                        current_teacher_subject = exam_teacher_subject_instance.teacher_subject
                        
                        existing_teacher_subject = TeacherSubject.objects.filter(
                            teacher=current_teacher_subject.teacher,
                            subject=subject
                        ).order_by('created_at').last()
                        
                        exam_teacher_subject_instance.teacher_subject = existing_teacher_subject
                        exam_teacher_subject_instance.save()
                        
                        # if subdiscipline_id:
                        #     subdiscipline = Subject.objects.get(pk=subdiscipline_id)
                        #     subject.parent_subject = subdiscipline
                        #     subject.save()
                        
                        Question.objects.filter(examquestion__exam_teacher_subject=exam_teacher_subject_instance).update(subject=subject)
                    
                    return Response(
                        ExamTeacherSubjectSerializer(exam_teacher_subject.instance).data, 
                        status=status.HTTP_200_OK
                    )
            else:
                return Response(
                    {"error": "Certifique-se que não deixou campos em branco"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        except ExamTeacherSubject.DoesNotExist:
            return Response(
                {"error": "ExamTeacherSubject not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            print(repr(e))
            logger.exception(f"Erro ao atualizar o professor: {repr(e)}")
            return Response(status=status.HTTP_400_BAD_REQUEST)


    @action(detail=True, methods=['post'])
    def create_exam_question(self, request, pk=None):
        question = request.data

        question_instance = Question.objects.using('default').get(pk=question.get('id') or question.get('pk'))

        try:
            #Aparentemtne quando selecionando na lsita de questões autorais na experincia antigo de professor, não vem nesse formato e a linha abaixo quebra
            if question_instance.category == Question.CHOICE:
                corretas = [alt for alt in question['alternatives'] if alt.get('isCorrect', False)]
                
                can_not_add_multiple_correct_options_question = True
                
                if self.request.user.questions_configuration:
                    can_not_add_multiple_correct_options_question = self.request.user.questions_configuration.can_not_add_multiple_correct_options_question
                
                client_has_module_disable_multiple_correct_options = request.user.client_can_disable_multiple_correct_options
                
                if client_has_module_disable_multiple_correct_options and can_not_add_multiple_correct_options_question and len(corretas) > 1:
                    return Response({ 
                        "error": f"Questão possui mais de uma alternativa correta.",
                    }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            pass

        try:
            
            teacher_subject = ExamTeacherSubject.objects.using('default').get(pk=pk) # alterar para source_exam_teacher_subject
            
            exam = teacher_subject.exam
            exam_questions = teacher_subject.examquestion_set.availables()
            question_is_discursive = question_instance.category == Question.TEXTUAL or question_instance.category == Question.FILE
            discursive_limit_hit = exam_questions.filter(question__category__in=[Question.TEXTUAL, Question.FILE]).count() >= teacher_subject.discursive_quantity
            question_is_objective = question_instance.category == Question.CHOICE
            objective_limit_hit = exam_questions.filter(question__category=Question.CHOICE).count() >= teacher_subject.objective_quantity
            total_limit_hit = exam_questions.count() >= teacher_subject.quantity
            
            if question_instance in exam.questions.all():
                return handle_question_duplication()

            if teacher_subject.block_questions_quantity:
                has_error = False
                msg = ''

                if teacher_subject.objective_quantity and teacher_subject.discursive_quantity:

                    if teacher_subject.quantity > teacher_subject.objective_quantity + teacher_subject.discursive_quantity:
                        if total_limit_hit:
                            has_error = True
                            msg = f"Você atingiu o limite máximo de questões que podem ser inseridas neste caderno"
                        if discursive_limit_hit and not objective_limit_hit and question_is_discursive:
                            has_error = True
                            msg = f"Complete a quantidade de questões objetivas antes de adicionar mais discursivas"

                        if not discursive_limit_hit and objective_limit_hit and question_is_objective:
                            has_error = True
                            msg = f"Complete a quantidade de questões discursivas antes de adicionar mais objetivas"
                    else:    
                        if question_is_discursive and discursive_limit_hit:
                            has_error = True
                            msg = f"Você atingiu o limite permitido para questão {question_instance.get_category_display().lower()}"
                            
                        elif question_is_objective and objective_limit_hit:
                            has_error = True
                            msg = f"Você atingiu o limite permitido para questão {question_instance.get_category_display().lower()}"
                    
                elif teacher_subject.objective_quantity:
                    if question_is_objective and objective_limit_hit:
                        has_error = True
                        msg = f"Você atingiu o limite permitido para questão {question_instance.get_category_display().lower()}"
                    elif question_is_discursive:
                        has_error = True
                        msg = "Você não pode adicionar questões discursivas nessa solicitação"
                    
                elif teacher_subject.discursive_quantity:
                    if question_is_discursive and discursive_limit_hit:
                        has_error = True
                        msg = f"Você atingiu o limite permitido para questão {question_instance.get_category_display().lower()}"
                    elif question_is_objective:
                        has_error = True
                        msg = "Você não pode adicionar questões objetivas nessa solicitação"
                        
                    
                if has_error:
                    return Response(msg, status=status.HTTP_401_UNAUTHORIZED)
                
            if teacher_subject.block_quantity_limit and exam_questions.count() >= teacher_subject.quantity:
                return Response("Você atingiu o limite máximo de questões que podem ser inseridas neste caderno", status=status.HTTP_401_UNAUTHORIZED)
                
            if question_instance.is_public:
                question_instance = question_instance.duplicate_question(self.request.user)
            
            biggest_order = teacher_subject.examquestion_set.using('default').all().order_by('-order').first()

            question_is_late = teacher_subject.exam.elaboration_deadline < timezone.now().date() if teacher_subject.exam.elaboration_deadline else False
            exam_question = ExamQuestion.objects.using('default').create(
                exam=exam,
                exam_teacher_subject=teacher_subject,
                weight=question.get('weight'),
                order=(biggest_order.order + 1) if biggest_order else 0,
                question=question_instance,
                is_late=question_is_late,
                block_weight=question.get('block_weight') if question.get('block_weight')  else False,
            )
            exam.distribute_weights(exam_teacher_subject=teacher_subject)

        except Exception as e:
            
            return Response({ 
                "error": f"{repr(e)}",
                "message": f"Erro ao tentar vincular a questão ao caderno"
            }, status=status.HTTP_400_BAD_REQUEST)
            
        return Response(ExamQuestionSerializer(instance=exam_question).data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def delete_exam_question(self, request, pk=None):
        user = request.user
        
        try:
            exam_question = ExamQuestion.objects.using('default').get(pk=pk)
            exam = exam_question.exam
            
            if hasattr(user, 'inspector') and not exam_question.can_be_remove:
                return Response("Você não pode deletar a questão, pois a mesma já foi aprovada ou utilizada em algum caderno ou você não tem permissão para realizar esta ação.", status=status.HTTP_401_UNAUTHORIZED)
            
            exam_question.delete()
            
            exam_questions = exam.examquestion_set.using('default').availables(exclude_annuleds=True)
            
            if exam_question in exam_questions:
                
                exam.distribute_weights(exam_teacher_subject=exam_question.exam_teacher_subject)

        except Exception as e:
            print(repr(e))
            logger.exception(f"Erro ao remover a questão do caderno: {repr(e)}")
            return Response(status=status.HTTP_400_BAD_REQUEST)
            
        return Response({"message": "Questão Removida"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post', 'put'])
    def create_update_material(self, request, pk=None):
        try:
            if request.method == 'PUT':
                request.data._mutable = True
                material = request.data
                if type(material.get('thumbnail')) == str:
                    material.pop('thumbnail')
                if type(material.get('material')) == str:
                    material.pop('material')

                exam_material = StudyMaterialSimpleSerializer(instance=StudyMaterial.objects.using('default').get(pk=pk), data=material)
                exam_material.is_valid(raise_exception=True)
                exam_material.save()
                
            if request.method == 'POST':
                exam_material = StudyMaterialSimpleSerializer(data=request.data)
                exam_material.is_valid(raise_exception=True)
                exam_material.save(exam=Exam.objects.using('default').get(pk=pk), client=request.user.get_clients()[0])

        except Exception as e:
            return Response(exam_material.errors, status=status.HTTP_400_BAD_REQUEST)    
        
        return Response(exam_material.data, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['post'])
    def delete_material(self, request, pk=None):
        try:
            exam_material = StudyMaterial.objects.using('default').get(pk=pk)
            exam_material.delete()
        except Exception as e:
            logger.exception(f"Erro ao remover o material: {repr(e)}")
            return Response(status=status.HTTP_400_BAD_REQUEST)
            
        return Response({"message": "Material Removido"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def distribute_weights(self, request, pk=None):
        examquestion = request.data.get('question')
        weights = request.data.get('weights')
        weight = float(request.data.get('weight', 0))
        
        try:
            if examquestion:
                exam_question = ExamQuestion.objects.using('default').get(pk=examquestion['id'])
                exam_question.weight = round_half_up(float(examquestion['weight']), 6)
                exam_question.save()
            else:
                exam_teacher_subject = ExamTeacherSubject.objects.using('default').get(pk=pk)
                exam_questions = exam_teacher_subject.examquestion_set.using('default').availables()
                if weights or weight and exam_questions.count():
                    if weight and not exam_teacher_subject.subject_note:
                        new_value = round_half_up(weight / exam_questions.count(), 6)
                        for exam_question in exam_questions:
                            exam_question.weight = float(exam_question.weight) + new_value
                            exam_question.save()
                    else:
                        if exam_questions.count():
                            new_value = round_half_up(float(weights) / exam_questions.count(), 6)
                            exam_teacher_subject.examquestion_set.all().update(weight=new_value)
                        else:
                            exam_teacher_subject.examquestion_set.all().update(weight=0)

                return Response({ 
                    "sum_weight": exam_questions.aggregate(sum=Sum('weight')).get("sum", 0), 
                    "exam_questions": ExamQuestionVerySimpleSerializer(instance=exam_teacher_subject.examquestion_set.using('default').all(), many=True).data}, 
                    status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Erro ao distribuir os pesos: {repr(e)}")
            return Response({ 
                "error": f"{repr(e)}",
                "message": f"Erro ao tentar distribuir pesos para as questões"
            }, status=status.HTTP_400_BAD_REQUEST)
        return Response(request.data, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['put'])
    def swap_position(self, request):
        try:
            
            if request.data.get('teacher_subjects'):
                
                exam = Exam.objects.get(pk=ExamTeacherSubject.objects.using('default').get(pk=request.data.get('teacher_subjects')[0].get('id')).exam.id)
                
                if not exam.can_edit_content():
                    raise BadRequest("A ordem não pode ser alterada. O caderno já está fechado ou possui malote gerado.")
                
                exam_teachers_subject = exam.examteachersubject_set.all().order_by('-order')
                biggest_order = exam_teachers_subject.first().order + 1
                
                for exam_teacher_subject in exam_teachers_subject:
                    exam_teacher_subject.order = int(biggest_order + exam_teacher_subject.order)
                    exam_teacher_subject.save()
                    
                for (index, _exam_teacher_subject) in enumerate(request.data.get('teacher_subjects')):
                    exam_teacher_subject = ExamTeacherSubject.objects.using('default').get(pk=_exam_teacher_subject.get('id'))
                    exam_teacher_subject.order = index
                    _exam_teacher_subject['order'] = index
                    exam_teacher_subject.save()
            else:
                for (index, _exam_question) in enumerate(request.data.get('exam_questions')):
                    
                    exam_question = ExamQuestion.objects.using('default').get(pk=_exam_question.get('id'))

                    if not exam_question.exam.can_edit_content():
                        raise BadRequest("A ordem não pode ser alterada. O caderno já está fechado ou possui malote gerado.")
                    
                    old_order = exam_question.order

                    exam_question_with_old_position = ExamQuestion.objects.using('default').filter(
                        exam_teacher_subject=exam_question.exam_teacher_subject,
                        order=index
                    ).first()
                    
                    if exam_question_with_old_position:
                        exam_question_with_old_position.order = 1000
                        exam_question_with_old_position.save(skip_hooks=True)
                        
                    exam_question.order = index
                    _exam_question['order'] = index
                    exam_question.save()
                    
                    if exam_question_with_old_position:
                        exam_question_with_old_position.order = old_order
                        exam_question_with_old_position.save(skip_hooks=True)

            if request.data.get('teacher_subjects'):
                request.data.get('teacher_subjects').sort(key=lambda x: x['order'])
            else:
                request.data.get('exam_questions').sort(key=lambda x: x['order'])
                
        except Exception as e:
            logger.exception(f"Erro ao alterar as posição das questão: {repr(e)}")
            return Response(f"Ocorreu um problema: {e}", status=status.HTTP_400_BAD_REQUEST)
        
        return Response(request.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['PATCH'])
    def change_release_material_date(self, request, pk=None):
        try:
            self.get_object().materials.all().update(release_material_study=request.data.get('release_material_study'))
        except Exception as e:
            logger.exception(f"Erro ao alterar a data de liberação do material: {repr(e)}")
            return Response(status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['GET'])
    def get_status_count(self, request, pk=None):
        try:
            exam_teacher_subject = ExamTeacherSubject.objects.using('default').get(pk=request.GET.get('exam_teacher_subject'))
            total = 0
            data = {}
            for statusquestion in StatusQuestion.STATUS_CHOICES:
                if statusquestion[0] == StatusQuestion.OPENED:
                    continue
                
                data[statusquestion[1]] = StatusQuestion.objects.filter(
                    status=statusquestion[0],
                    exam_question__exam_teacher_subject=exam_teacher_subject,
                    active=True
                ).distinct().count()

                total += data[statusquestion[1]]

            data["Em aberto"] = exam_teacher_subject.quantity - total
            return Response(data=data, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.exception(f"Erro tentar retornar status das questões do professor: {repr(e)}")
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=True, methods=['post'])
    def change_foreign_language(self, request, pk=None):
        try:
            exam = self.get_object()
            exam_teachers = ExamTeacherSubject.objects.using('default').filter(exam=exam)
            exam_teachers.update(is_foreign_language=False)
            if request.data:
                exam_teachers.filter(pk__in=request.data).update(is_foreign_language=True)
            return Response(status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(f"Erro ao atualizar os professores de lingua estrangeira: {repr(e)}")
        return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def get_opened_exams(self, request, pk=None):
        teacher = self.request.user.inspector
        user = self.request.user
        
        queryset = ExamTeacherSubject.objects.filter(
            Q(
                Q(exam__coordinations__unity__client__in=user.get_clients_cache()),
                Q(teacher_subject__teacher=teacher),
                Q(exam__status=Exam.ELABORATING),
                Q(
                    Q(exam__release_elaboration_teacher__lte=timezone.now())|
                    Q(exam__release_elaboration_teacher__isnull=True)
                )
            )
        ).order_by(
            'exam__elaboration_deadline'
        ).exclude(
            # Q(
            #     Q(exam__category=Exam.HOMEWORK, exam__created_by=user)
            # ) |
            Q(
                Q(exam__application__applicationstudent__start_time__isnull=False) |
                Q(exam__application__applicationstudent__is_omr=True)
            )
        ).distinct().detailed_status()
        
        if self.request.GET.get('opened_exams_type') == 'opened':
            queryset = queryset.filter(count_total_questions=0)
        elif self.request.GET.get('opened_exams_type') == 'elaborating':
            queryset = queryset.filter(count_total_questions__gte=0)
        
        if self.request.GET.get('opened_exams_deadline') == 'on_time':
            queryset = queryset.filter(exam__elaboration_deadline__gt=timezone.now())
        elif self.request.GET.get('opened_exams_deadline') == 'late':
            queryset = queryset.filter(exam__elaboration_deadline__lt=timezone.now())

        if self.request.GET.get('exam_name', None):
            queryset = queryset.filter(exam__name__icontains=self.request.GET.get('exam_name', None))

        
        paginator = SimpleAPIPagination()
        instances = paginator.paginate_queryset(queryset, request)

        serializer = ExamTeacherSubjectOpenedOrToReviewSerializer(instances, many=True, context={"request": self.request, "use_teacher_subject": True})
        
        return paginator.get_paginated_response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def get_exams_to_review(self, request, pk=None):
        
        user = self.request.user
        
        teacher = user.inspector
        
        return_exam = self.request.GET.get('return_exam', None) 
        
        if return_exam:
        
            queryset = teacher.get_exams_to_review()
        
        else:
            
            queryset = teacher.get_exams_to_review(return_exam_teacher_subjects=True).annotate(
                count=Count('examquestion', distinct=True),
                count_reviewed_questions=Count('examquestion', filter=Q(examquestion__statusquestion__user=user), distinct=True)
            ).filter(count__gt=0).exclude(count_reviewed_questions=F('count'))
            
            if self.request.GET.get('exams_to_review_type') == 'await_review':
                queryset = queryset.filter(count_reviewed_questions=0)
            elif self.request.GET.get('exams_to_review_type') == 'in_review':
                queryset = queryset.filter(count_reviewed_questions__gt=0)
        
        paginator = SimpleAPIPagination()
        
        instances = paginator.paginate_queryset(queryset.annotate(
            user_pk=Value(user.pk, output_field=UUIDField())
        ), request)
        
        serializer = ExamToReviewSerializer(instances, many=True) if return_exam else ExamTeacherSubjectOpenedOrToReviewSerializer(instances, many=True, context={"request": self.request})
        
        return paginator.get_paginated_response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def get_exams_to_review_count(self, request, pk=None):
        
        user = self.request.user
        
        teacher = user.inspector
        
        return_exam = self.request.GET.get('return_exam', None) 
        
        if return_exam:
        
            queryset = teacher.get_exams_to_review()
        
        else:
            
            queryset = teacher.get_exams_to_review(return_exam_teacher_subjects=True).annotate(
                count=Count('exam__examquestion', distinct=True),
                count_reviewed_questions=Count('exam__examquestion', filter=Q(exam__examquestion__statusquestion__user=user), distinct=True)
            ).filter(count__gt=0).exclude(count_reviewed_questions=F('count'))
            
            if self.request.GET.get('exams_to_review_type') == 'await_review':
                queryset = queryset.filter(count_reviewed_questions=0)
            elif self.request.GET.get('exams_to_review_type') == 'in_review':
                queryset = queryset.filter(count_reviewed_questions__gt=0)
        

        return Response(queryset.count())
    
    @action(detail=True, methods=['GET'])
    def get_exam_questions(self, request, pk=None):
        
        exam = self.get_object()
        
        exam_questions = exam.examquestion_set.filter(
            Q(statusquestion__isnull=True) |
            Q(
                statusquestion__status__in=[StatusQuestion.APPROVED, StatusQuestion.REPROVED, StatusQuestion.OPENED, StatusQuestion.CORRECTION_PENDING, StatusQuestion.CORRECTED, StatusQuestion.SEEN, StatusQuestion.ANNULLED, StatusQuestion.USE_LATER], 
                statusquestion__active=True
            )
        )
        
        if request.GET.get('exam_teacher_subject_pk'):
            exam_teacher_subject = ExamTeacherSubject.objects.using('default').get(pk=request.GET.get('exam_teacher_subject_pk'))
            return Response(data=ExamQuestionSerializer(instance=exam_questions.filter(exam_teacher_subject=exam_teacher_subject).distinct(), many=True, read_only=True, context={'request': request}).data)
        
        if self.request.GET.get('exclude_teacher'):
            exam_questions = exam_questions.exclude(exam_teacher_subject__in=self.request.GET.getlist('exclude_teacher'))
            
        return Response(data=ExamQuestionSerializer(instance=exam_questions.distinct(), many=True, read_only=True, context={'request': request}).data)
    
    @action(detail=False, methods=['PATCH'])
    def change_status(self, request, pk=None):
        """
            Essa altera o status de vários cadernos ao mesmo tempo
            Body: {
                ids: [1,2,3,4,5]
                status: 1,
            }
        """
        try:
            Exam.objects.using('default').filter(id__in=request.data.get('ids')).update(status=self.request.data.get('status'))
            return Response(status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(f"Não foi possível alterar os status dos cadernos selecionados: {repr(e)}")
            return Response(status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=True, methods=['PATCH'])
    def change_is_printed(self, request, pk=None):
        """
            Essa função altera o campo is_printed.
            Caso True ele colocar False e vice-versa
        """
        try:
            object = Exam.objects.using('default').get(pk=pk)
            object.is_printed = (not object.is_printed)
            object.save()
        
            return Response(status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(f"Não foi possível alterar os status dos cadernos selecionados: {repr(e)}")
            return Response(status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['GET'])
    def get_blocked_weights(self, request, pk):
        """
            Retorna a soma dos pessos que estão bloqueados no caderno
        """
        try:
            exam = Exam.objects.get(pk=pk) # aqui posso passar a query de exams pois o retorno é apenas o valor bloqueado no caderno
            return Response(data=exam.get_blocked_weights, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.exception(f"Não foi possível retornar os pesos bloqueados do caderno: {repr(e)}")
            return Response(data=0,status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=True, methods=['GET'])
    def get_sum_weight(self, request, pk=None):
        exam = self.get_object()
        if request.data.get('recalculate'):
            exam.distribute_weights()
        return Response(ExamSumWeightSerializer(instance=exam).data)
    
    @action(detail=False, methods=['POST'])
    def get_unities_and_classes(self, request, pk=None):
        exams_ids = request.data
        user = self.request.user
        coordinations = user.get_coordinations_cache()
        exams = Exam.objects.filter(coordinations__in=coordinations, id__in=exams_ids)
        applications_student = ApplicationStudent.objects.filter(application__exam__in=exams)
        
        unities = Unity.objects.filter(coordinations__in=coordinations).distinct()
                
        classes = SchoolClass.objects.annotate(
            unity_name=F("coordination__unity__name")
        ).filter(
            pk__in=applications_student.values_list('student__classes'),
            coordination__in=coordinations,
            school_year__in=exams.order_by('application__created_at').values('application__date__year'),
        ).distinct()
        
        object = {
            "unities": unities.values('id', 'name'),
            "classes": classes.values('id', 'name', 'unity_name'),
        }
        
        return Response(object)
    
    @action(detail=True, methods=['GET'])
    def get_exam_questions_number(self, request, pk=None):
        
        exam = self.get_object()
        exam_questions = exam.examquestion_set.all()
            
        return Response(data=ExamQuestionNumberSerializer(instance=exam_questions.distinct(), many=True).data)

    @action(detail=True, methods=['GET'], parser_classes = [CamelCaseJSONParser], renderer_classes = [CamelCaseJSONRenderer])
    def get_applications_student(self, request, pk=None):
        from fiscallizeon.applications.serializers.application import ApplicationStudentSerializer
        exam = self.get_object()
        school_class = self.request.GET.get('school_class')
        
        applications_student = ApplicationStudent.objects.filter(
            Q(application__exam=exam),
            Q(
                Q(student__classes=school_class) if school_class else Q(),
            )
        )
        
        return Response(ApplicationStudentSerializer(instance=applications_student.distinct(), many=True).data)
    
    @action(detail=True, methods=['GET'], parser_classes = [CamelCaseJSONParser], renderer_classes = [CamelCaseJSONRenderer])
    def get_applications_student_with_essay_answer(self, request, pk=None):
        from fiscallizeon.answers.serializers.file_answers import FileAnswerWithImgAnnotationsSerializer
        from fiscallizeon.answers.models import FileAnswer
        
        school_class = self.request.GET.get('school_class')
        
        student = self.request.GET.get('student')
        
        applications_student = ApplicationStudent.objects.filter(
            Q(application__exam=self.get_object()),
            Q(student__classes=school_class) if school_class else Q(),
            Q(student=student) if student else Q(),
        )
        
        class OutputSerializer(serializers.ModelSerializer):
            student = serializers.SerializerMethodField()
            answer = serializers.SerializerMethodField()
            
            class Meta:
                model = ApplicationStudent
                fields = ['id', 'student', 'answer']
            
            def get_answer(self, obj):
                answer = FileAnswer.objects.filter(student_application=obj, question__is_essay=True).first()
                return FileAnswerWithImgAnnotationsSerializer(instance=answer).data
                
            def get_student(self, obj):
                return {
                    "name": obj.student.name,
                }
                
        return Response(OutputSerializer(instance=applications_student, many=True).data)
    
    @action(detail=True, methods=['GET'], parser_classes = [CamelCaseJSONParser], renderer_classes = [CamelCaseJSONRenderer], required_permissions = [settings.COORDINATION,  settings.TEACHER, settings.STUDENT])
    def get_application_student_essay_answer(self, request, pk=None):
        from fiscallizeon.answers.serializers.file_answers import FileAnswerWithImgAnnotationsSerializer
        from fiscallizeon.answers.models import FileAnswer
        user = self.request.user
        
        if user.user_type == 'student':
            application_student = user.student.applicationstudent_set.get(pk=pk)
        else:
            application_student = ApplicationStudent.objects.get(pk=pk)
        
        essay_answer = FileAnswer.objects.filter(student_application=application_student, question__is_essay=True).first()
        return Response(FileAnswerWithImgAnnotationsSerializer(instance=essay_answer).data)

class ExamDestroyAPIView(LoginRequiredMixin, CheckHasPermission, generics.DestroyAPIView):
    queryset = Exam.objects.all()
    required_permissions = [settings.COORDINATION,  settings.TEACHER,]
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        user = self.request.user

        if user.is_authenticated and user.user_type == 'teacher' and not instance.created_by == user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        try:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_200_OK)
        except ProtectedError:
            return Response(status=status.HTTP_302_FOUND)

    def perform_destroy(self, instance):
        instance.delete()

class ExamCustomPageDestroyAPIView(LoginRequiredMixin, CheckHasPermission, generics.DestroyAPIView):
    queryset = ClientCustomPage.objects.all()
    required_permissions = [settings.COORDINATION,  settings.TEACHER,]
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        try:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_200_OK)
        except ProtectedError:
            return Response(status=status.HTTP_302_FOUND)

    def perform_destroy(self, instance):
        instance.delete()
        
class BackgroundsDestroyAPIView(LoginRequiredMixin, CheckHasPermission, generics.DestroyAPIView):
    queryset = ExamBackgroundImage.objects.all()
    required_permissions = [settings.COORDINATION,]
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        try:
            self.perform_destroy(instance)
            return Response(status=status.HTTP_200_OK)
        except ProtectedError:
            return Response(status=status.HTTP_302_FOUND)

    def perform_destroy(self, instance):
        instance.delete()
        
class ExamTeacherSubjectFromExamAPIView(LoginRequiredMixin, CheckHasPermission, ListAPIView):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    authentication_classes = (CsrfExemptSessionAuthentication, )
    serializer_class = ExamTeacherSubjectSimpleSerializer

    def get_queryset(self):
        exam_pk = self.request.GET.get('exam_pk')

        queryset = ExamTeacherSubject.objects.filter(exam__pk=exam_pk) if exam_pk != "" else None

        if self.request.user.user_type == settings.TEACHER:
            queryset = queryset.filter(
                teacher_subject__teacher__user=self.request.user
            )

        return queryset.distinct()

class ExamQuestionCopyAPIView(LoginRequiredMixin, CheckHasPermission, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    required_permissions = [settings.COORDINATION,  settings.TEACHER,]
    
    def post(self, request, *args, **kwargs):
        status_to_exclude = [StatusQuestion.REPROVED]
        
        exam_question_to_copy = ExamQuestion.objects.get(pk=request.data.get("examQuestionToCopy"))
        destination_exam = Exam.objects.get(pk=request.data.get("destinationExam"))
        destination_exam_teacher_subject = ExamTeacherSubject.objects.get(pk=request.data.get("destinationExamTeacherSubject"))
        destination_exam_questions = ExamQuestion.objects.filter(exam__pk=destination_exam.pk)
        exam_questions_at_destination_exam_teacher_subject = destination_exam_questions.filter(exam_teacher_subject__pk=destination_exam_teacher_subject.pk).exclude(statusquestion__active=True, statusquestion__status__in=status_to_exclude)
        duplicate_question = request.data.get("duplicateQuestion")
        keep_question_data = request.data.get("keepQuestionData")
        
        # para casos de duplicação para fazer alterações no question, remover a examquestion antiga
        remove_old_exam_question = request.data.get("removeOldExamQuestion")
        old_pk = exam_question_to_copy.pk

        if destination_exam_teacher_subject.block_quantity_limit and exam_questions_at_destination_exam_teacher_subject.count() == destination_exam_teacher_subject.quantity:
            return Response("Limite de questões da solicitação de destino excedido", status=400)
        
        if destination_exam_questions.filter(question=exam_question_to_copy.question).exists() and not duplicate_question:
            return Response("A questão já existe no caderno de destino", status=400)
            
        if duplicate_question:
            if keep_question_data:
                duplicated_question = exam_question_to_copy.question.duplicate_question_with_conditions(user=self.request.user, keep_pedagogical_data=True, keep_alternatives=True)
            else:
                duplicated_question = exam_question_to_copy.question.duplicate_question(user=self.request.user)

            exam_question_to_copy.question = duplicated_question

        biggest_order = destination_exam_teacher_subject.examquestion_set.using('default').all().order_by('-order').first()

        try:
            new_exam_question = ExamQuestion.objects.using('default').create(
                exam=destination_exam,
                exam_teacher_subject=destination_exam_teacher_subject,
                question=exam_question_to_copy.question,
                weight=exam_question_to_copy.weight if keep_question_data else Decimal(1.0000),
                order=biggest_order.order + 1 if biggest_order else 0,
            )
        except:
            return Response("Ocorreu um erro inesperado ao copiar a questão", status=400)

        return Response(exam_question_to_copy.pk, status=200)
    

class ExamBagExistenceCheckView(APIView):
    
    def get(self, request, pk):
        exam = Exam.objects.get(id=pk)
        existis_bag = exam.check_is_bag_exist()

        return Response({
            'exists': existis_bag,
        }, status=status.HTTP_200_OK)
    


exam_bag_existence_check = ExamBagExistenceCheckView.as_view()

exams_api_list = ExamListView.as_view()

exam_teacher_subjects_from_exam = ExamTeacherSubjectFromExamAPIView.as_view()
exam_question_copy = ExamQuestionCopyAPIView.as_view()

exam_api_detail = ExamRetrieveAPIView.as_view()
exams_status_question_api_create = StatusQuestionCreate.as_view()
exams_status_question_api_update = StatusQuestionUpdate.as_view()
exams_status_tags_api_create = QuestionTagStatusQuestionCreate.as_view()

exams_template_api_list = ExamTemplateListView.as_view()

exams_api_delete_all = ExamDestroyAPIView.as_view()
custom_pages_delete_all = ExamCustomPageDestroyAPIView.as_view()

revert_status_question_api_view = RevertStatusQuestionAPIView.as_view()