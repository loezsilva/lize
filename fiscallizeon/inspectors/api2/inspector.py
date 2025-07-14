from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction

from django.utils import timezone
from django.db import IntegrityError
from django.db.models import Q

from fiscallizeon.inspectors.models import Inspector, TeacherSubject
from fiscallizeon.exams.serializers.exams import ExamTeacherSubjectCreateSimpleSerializer 
from fiscallizeon.inspectors.serializers2.inspector import (
    InspectorSerializer, 
    InspectorWithPermissionGroupsSerializer, 
    InspectorTeacherSubjectsSerializer, 
    TeacherSubjectPkSerializer,
    CreateExamAndExamTeacherSubjectSerializer
)
from fiscallizeon.inspectors.permissions import IsInspectorOwner
from fiscallizeon.core.paginations import LimitOffsetPagination
from fiscallizeon.clients.models import CoordinationMember
from fiscallizeon.accounts.models import User
from fiscallizeon.exams.models import Exam
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.subjects.models import Subject, Grade


import django_filters


class InspectorFilterSet(django_filters.FilterSet):
    is_active = django_filters.BooleanFilter(method='is_active_method')
    school_year = django_filters.CharFilter(
        field_name='teachersubject__classes__school_year',
        lookup_expr='exact'
    )

    def is_active_method(self, queryset, name, value):
        if value is None:
            return queryset

        if value:
            return queryset.filter(user__is_active=True)
        else:
            return queryset.filter(
                Q(user__isnull=True) |
                Q(user__is_active=False)
            )

    class Meta:
        model = Inspector
        fields = ['email', 'school_year', 'is_active', ]

@extend_schema(tags=['Professores'])
class InspectorViewSet(viewsets.ModelViewSet):
    serializer_class = InspectorWithPermissionGroupsSerializer
    permission_classes = [IsInspectorOwner]
    pagination_class = LimitOffsetPagination
    filterset_class = InspectorFilterSet

    def get_queryset(self):
        return Inspector.objects.filter(
            coordinations__in=self.request.user.get_coordinations_cache()
        ).distinct()
    
    def create(self, request, *args, **kwargs):
        serializer = InspectorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        instance = Inspector.objects.filter(
            email=serializer.validated_data.get("email"),
            coordinations__unity__client=self.request.user.client,
        ).first()

        if instance:
            user = instance.user

            if not user:
                email = serializer.validated_data.get("email")
                user = User.objects.filter(email=email).first()
                if user:
                    instance.user = user
                    instance.save()

            if user and not user.is_active:
                user.is_active = True
                user.save()
        else:
            serializer.save()

        user = self.request.user
        
        # Adiciona grupos padrão ao criar um professor
        if groups := self.request.data.get('permission_groups', []):
            for group in groups:
                instance.user.custom_groups.add(group)
            
        else:
            # Se o cliente tiver algum grupo padrão eu seto esses grupos
            # se não eu pego os grupos padrões da Lize
            if user.client.has_default_groups('teacher'):
                groups = user.client.get_groups().filter(client__isnull=False, segment='teacher', default=True)
                for group in groups:
                    instance.user.custom_groups.add(group)
            else:
                groups = user.client.get_groups().filter(client__isnull=True, segment='teacher', default=True)
                for group in groups:
                    instance.user.custom_groups.add(group)
        
        headers = self.get_success_headers(serializer.data)

        # CoordinationMember.objects.filter(
        #     user=instance.user
        # ).delete()
        
        return Response(self.serializer_class(instance=instance).data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        """ 
            Essa lógica não pode ser alterada sem testar o fluxo de criar e atualizar professores
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = InspectorSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if groups := self.request.data.get('permission_groups', []):
            for group in groups:
                instance.user.custom_groups.add(group)
        
        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        instance.clean_coordinations_cache()

        #comentado após a criação do recurso de professor também coordenador
        # CoordinationMember.objects.filter(
        #     user=instance.user
        # ).delete()

        return Response(self.serializer_class(instance=instance).data)

    def destroy(self, request, pk):
        try:
            return super(InspectorViewSet, self).destroy(request, pk)
        except IntegrityError:
            inspector = self.get_object()
            if inspector.user:
                if inspector.user.can_navigate_between_profiles:
                    inspector.user = None
                    inspector.save(skip_hooks=True)
                else:
                    inspector.user.is_active = False
                    inspector.user.save()          
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], serializer_class=InspectorTeacherSubjectsSerializer)
    def add_subjects(self, request, pk=None):
        
        inspector = self.get_object()

        if not inspector.user:
            inspector.user = User.objects.filter(email=inspector.email).first()
            inspector.user.is_active = True
            inspector.user.save()
            inspector.save(skip_hooks=True)

        data = request.data
        subject = data.get('subject')
        
        teacher_subject = inspector.teachersubject_set.filter(
            subject=subject,
            school_year=timezone.now().year
        ).first()

        if not teacher_subject:
            teacher_subject = inspector.teachersubject_set.filter(
                subject=subject
            ).first()
        
        if teacher_subject and not teacher_subject.active:
            teacher_subject.active = True
            teacher_subject.school_year = timezone.now().year
            teacher_subject.save(skip_hooks=True)
        
        serializer = self.get_serializer(instance=teacher_subject, data=data)
        serializer.is_valid(raise_exception=True)
        
        serializer.save(teacher=inspector)
            
        return Response(serializer.data)
    
    @action(detail=True, methods=['delete'])
    def remove_subjects(self, request, pk):
        serializer = TeacherSubjectPkSerializer(data=request.data)
        if serializer.is_valid():
            inspector = self.get_object()
            teacher_subjects = inspector.teachersubject_set.filter(
                subject__in=serializer.data['subjects']
            )
            teacher_subjects.filter(examteachersubject__isnull=True).delete()
            teacher_subjects.filter(examteachersubject__isnull=False).update(active=False)
            return self.retrieve(request, pk)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['POST'], permission_classes=[], authentication_classes=[CsrfExemptSessionAuthentication])
    def create_homework(self, request, pk=None):
        user = self.request.user

        subject = request.data.get('subject')
        grade = request.data.get('grade')
        
        if not subject:
            return Response({ 
                'errors': {
                    'subject': ['Campo obrigatório']
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        if not grade:
            return Response({
                'errors': {
                    'grade': ['Campo obrigatório']
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            
            exam_serializer = CreateExamAndExamTeacherSubjectSerializer(data=request.data)
            exam_serializer.is_valid(raise_exception=True)
            exam_serializer.save(
                coordinations=user.get_coordinations(),
                created_by=user,
                category=Exam.HOMEWORK,
            )
            
            teacher_subject = {
                "exam": exam_serializer.instance.id,
                "teacher_subject": None,
                "quantity": 0,
                "grade": grade,
            }
            
            selected_teacher_subject = TeacherSubject.objects.using('default').get(teacher=user.inspector, subject=subject)
            teacher_subject['teacher_subject'] = selected_teacher_subject.id

            exam_teacher_subject_serialized = ExamTeacherSubjectCreateSimpleSerializer(data=teacher_subject)
            exam_teacher_subject_serialized.is_valid(raise_exception=True)
            exam_teacher_subject_serialized.save()    
            
            return Response(exam_serializer.data)
        
        return Response(status=status.HTTP_400_BAD_REQUEST)
        
    
    @action(detail=True, methods=['PATCH'], permission_classes=[], authentication_classes=[CsrfExemptSessionAuthentication])
    def update_homework(self, request, pk):
        
        user = self.request.user

        subject = request.data.get('subject')
        grade = request.data.get('grade')
        
        
        if not subject:
            return Response({ 
                'errors': {
                    'subject': ['Campo obrigatório']
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        if not grade:
            return Response({
                'errors': {
                    'grade': ['Campo obrigatório']
                }
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            
            subject_instance = Subject.objects.get(id=subject)
            grade_instance = Grade.objects.get(id=grade)
            
            exam_serializer = CreateExamAndExamTeacherSubjectSerializer(instance=Exam.objects.using('default').get(id=pk), data=request.data, partial=True)
            first_exam_teacher_subject = exam_serializer.instance.examteachersubject_set.using('default').first()
            exam_serializer.is_valid(raise_exception=True)
            exam_serializer.save()
            
            if first_exam_teacher_subject.teacher_subject.subject != subject_instance or first_exam_teacher_subject.grade != grade_instance:
                first_exam_teacher_subject.grade = grade_instance
                first_exam_teacher_subject.teacher_subject = TeacherSubject.objects.using('default').get(teacher=user.inspector, subject=subject_instance)
                first_exam_teacher_subject.save()
                
            return Response(exam_serializer.data)
        
        return Response(status=status.HTTP_400_BAD_REQUEST)

class CheckCoordinationAssociationAPI(APIView):
    def get(self, request, *args, **kwargs):
        email = request.query_params.get("email")

        if not email:
            return Response(
                {"error": "E-mail não fornecido"},
                status=status.HTTP_400_BAD_REQUEST
            )
                
        email_exists = CoordinationMember.objects.filter(user__email=email).exists()
        
        return Response({"email_exists": email_exists}, status=status.HTTP_200_OK)