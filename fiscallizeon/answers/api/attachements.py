import logging
from django.conf import settings
from fiscallizeon.answers.serializers.attachements import AttachmentsSerializer
from fiscallizeon.answers.models import Attachments
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from fiscallizeon.applications.models import ApplicationStudent

from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from rest_framework.authentication import BasicAuthentication
from fiscallizeon.core.utils import CheckHasPermission
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from fiscallizeon.exams.models import ExamTeacherSubject

logger = logging.getLogger()

class AttachmentsViewSet(viewsets.ModelViewSet):
    model = Attachments
    serializer_class = AttachmentsSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['exam_teacher_subject', 'application_student']

    def get_queryset(self):
        return self.model.objects.filter(application_student__student__user=self.request.user)

    @action(detail=False, methods=['get'], url_name="get-teacher-attachments") 
    def get_exam_teacher_subject_attachments(self, request, pk=None):
        user = self.request.user
        application_student = ApplicationStudent.objects.get(pk=request.GET.get('application_student'))
        
        try:
            exam_teacher_subject = ExamTeacherSubject.objects.filter(exam=application_student.application.exam)
            if not user.user_type == settings.COORDINATION:
                if user.user_type == settings.TEACHER and user.inspector.can_correct_questions_other_teachers:
                    exam_teacher_subject = exam_teacher_subject.filter(teacher_subject__subject__in=user.inspector.subjects.all())
                else:
                    exam_teacher_subject = exam_teacher_subject.filter(teacher_subject__teacher__user=user)
                    
            attachments = self.model.objects.filter(exam_teacher_subject__in=exam_teacher_subject, application_student=application_student)
            return Response(AttachmentsSerializer(attachments, many=True).data, status=status.HTTP_200_OK)
        
        except ExamTeacherSubject.DoesNotExist:
            attachments = self.model.objects.filter(application_student=application_student)
            return Response(AttachmentsSerializer(attachments, many=True).data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Erro ao tentar pegar os anexos: {repr(e)}")
            return Response(status=status.HTTP_400_BAD_REQUEST)