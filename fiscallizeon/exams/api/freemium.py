import logging

from ...exams.models import Exam, TeacherSubject, ExamTeacherSubject
from ...subjects.models import Subject
from ...classes.models import Grade

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from fiscallizeon.core.api import CsrfExemptSessionAuthentication


from djangorestframework_camel_case.parser import CamelCaseJSONParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer

from ..serializers.freemium import ExamFreemiumSerializer, ExamFreemiumCreateExamAndExamTeacherSubjectSerializer

from django.contrib.auth.mixins import UserPassesTestMixin

logger = logging.getLogger()

class ExamFreemiumViewset(UserPassesTestMixin, viewsets.ModelViewSet):
    serializer_class = ExamFreemiumSerializer
    authentication_classes = (CsrfExemptSessionAuthentication,)
    queryset = Exam.objects.all()
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    
    def test_func(self):
        self.user = self.request.user
        
        return self.user.is_authenticated and self.user.is_freemium
    
    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset().filter(created_by=user)
        
        return queryset
    
    
    @action(detail=False, methods=["POST"], serializer_class=ExamFreemiumCreateExamAndExamTeacherSubjectSerializer)
    def create_exam_teacher_subject(self, request, pk=None):
        data = self.request.data
        user = self.request.user
        teacher = user.inspector

        instance = ExamFreemiumCreateExamAndExamTeacherSubjectSerializer(data=data)
        instance.is_valid(raise_exception=True)
        
        exam = Exam.objects.create(
            name=instance.data.get('name'),
            created_by=user,
        )
        
        teacher_subject, created = TeacherSubject.objects.get_or_create(
            teacher=teacher,
            subject=Subject.objects.get(pk=instance.data.get('subject'))
        )
        
        exam_teacher_subject = ExamTeacherSubject.objects.create(
            exam=exam,
            teacher_subject=teacher_subject,
            grade=Grade.objects.get(pk=instance.data.get('grade')),
            quantity=0,
            elaboration_email_sent=True,
        )
        
        return Response(exam_teacher_subject.urls.get('add_questions'))
    
    @action(detail=True, methods=["PUT"], serializer_class=ExamFreemiumCreateExamAndExamTeacherSubjectSerializer)
    def update_exam_teacher_subject(self, request, pk=None):
        data = self.request.data
        user = self.request.user
        teacher = user.inspector
        
        instance = ExamFreemiumCreateExamAndExamTeacherSubjectSerializer(data=data)
        instance.is_valid(raise_exception=True)
        
        exam_teacher_subject = exam_teacher_subject = ExamTeacherSubject.objects.get(
            pk=pk,
            teacher_subject__teacher=teacher,
        )
        
        teacher_subject, created = TeacherSubject.objects.get_or_create(
            teacher=teacher,
            subject=Subject.objects.get(pk=instance.data.get('subject'))
        )
        
        exam_teacher_subject.exam.name = instance.data.get('name')
        exam_teacher_subject.teacher_subject = teacher_subject
        exam_teacher_subject.grade = Grade.objects.get(pk=instance.data.get('grade'))
        
        exam_teacher_subject.exam.save(skip_hooks=True)
        exam_teacher_subject.save(skip_hooks=True)
        
        return Response(instance.data)
    
    @action(detail=False, methods=["GET"], serializer_class=None)
    def credits(self, request, pk=None):
        user = self.request.user
        
        return Response({
            'availables': user.availables_credits,
            'can_create_ai_question': user.can_create_ai_question,
        })
        
    @action(detail=False, methods=["POST"], serializer_class=None)
    def interested_in_more_credits(self, request, pk=None):
        user = self.request.user
        user.interested_in_purchasing_more_credits = True
        user.save()
        return Response()