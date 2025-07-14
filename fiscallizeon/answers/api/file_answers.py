from django.conf import settings
from django.http import Http404
from rest_framework import serializers
from fiscallizeon.answers.serializers.file_answers import FileAnswerRemoveGradeSerializer, FileAnswerCreateFeedbackSerializer, FileAnswerImgAnnotationsSerializer, FileAnswerQRCodeSerializer, FileAnswerSerializer, FileAnswerFeedbackSerializer, FileAnswerTeacherCoordinationSerializer
from fiscallizeon.answers.models import FileAnswer
from fiscallizeon.answers.permissions import IsOwner, IsTeacherSubject

from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from rest_framework.authentication import BasicAuthentication 
from rest_framework import generics

from fiscallizeon.core.utils import CheckHasPermission, CheckHasPermissionAPI

import logging
logger = logging.getLogger()

class FileAnswerCreateView(generics.CreateAPIView):
    model = FileAnswer
    serializer_class = FileAnswerSerializer
    permission_classes = [IsOwner]
    authentication_classes = (CsrfExemptSessionAuthentication, )


class FileAnswerUpdateRetrieveView(generics.RetrieveUpdateAPIView):
    model = FileAnswer
    serializer_class = FileAnswerSerializer
    queryset = FileAnswer.objects.all()
    permission_classes = [IsOwner]
    authentication_classes = (CsrfExemptSessionAuthentication, )


class FileAnswerQRCodeCreateView(generics.CreateAPIView):
    model = FileAnswer
    serializer_class = FileAnswerQRCodeSerializer
    authentication_classes = [CsrfExemptSessionAuthentication]

class FileAnswerQRCodeRetrieveView(generics.RetrieveUpdateAPIView):
    model = FileAnswer
    serializer_class = FileAnswerQRCodeSerializer
    queryset = FileAnswer.objects.all()
    authentication_classes = [CsrfExemptSessionAuthentication]



class FileAnswerFeedbackUpdateView(generics.UpdateAPIView):
    model = FileAnswer
    serializer_class = FileAnswerFeedbackSerializer
    queryset = FileAnswer.objects.all()
    permission_classes = [IsTeacherSubject]
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    def get_object(self):
        question_id = self.request.data.get("question", None)
        student_application_id = self.request.data.get("student_application", None)
        try:
            file_answer = FileAnswer.objects.using('default').filter(pk=self.kwargs['pk']).first() or FileAnswer.objects.using('default').filter(question=question_id, student_application=student_application_id).first()
            if file_answer:
                return file_answer
            raise Http404
        except Http404:
            obj = FileAnswerCreateFeedbackSerializer(data=self.request.data)
            obj.is_valid(raise_exception=True)
            obj.save(corrected_but_no_answer=True)
            return obj.instance
        except Exception as e:
            return e
            

class FileAnswerResponseSearchListAPIView(generics.ListAPIView):
    model = FileAnswer
    serializer_class = FileAnswerSerializer
    permission_classes = [IsOwner]
    queryset = FileAnswer.objects.all()
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def get_queryset(self):
        queryset = super(FileAnswerResponseSearchListAPIView, self).get_queryset()
        queryset = queryset.filter(question__pk=self.request.GET.get('question'), student_application__pk=self.request.GET.get('student_application'))
        return queryset


class FileAnswerImgAnnotationsUpdateAPIView(generics.UpdateAPIView):
    model = FileAnswer
    serializer_class = FileAnswerImgAnnotationsSerializer
    permission_classes = []
    queryset = FileAnswer.objects.all()
    authentication_classes = (CsrfExemptSessionAuthentication, )

class FileAnswerImgAnnotationsRetrieveView(generics.RetrieveAPIView):
    model = FileAnswer
    serializer_class = FileAnswerImgAnnotationsSerializer
    queryset = FileAnswer.objects.all()
    permission_classes = []
    authentication_classes = (CsrfExemptSessionAuthentication, )


class FileAnswerTeacherCoordinationCreateView(CheckHasPermission, generics.CreateAPIView):
    model = FileAnswer
    serializer_class = FileAnswerTeacherCoordinationSerializer
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    authentication_classes = (CsrfExemptSessionAuthentication, )


class FileAnswerRemoveGradeUpdateView(CheckHasPermissionAPI, generics.UpdateAPIView):
    serializer_class = FileAnswerRemoveGradeSerializer
    queryset = FileAnswer.objects.all()
    authentication_classes = (CsrfExemptSessionAuthentication, )

class FileAnswerDeleteAnswerDeleteAPIView(CheckHasPermissionAPI, generics.DestroyAPIView):
    serializer_class = FileAnswerRemoveGradeSerializer
    queryset = FileAnswer.objects.all()
    authentication_classes = (CsrfExemptSessionAuthentication, )

class FileAnswerTeacherFeedbackUpdateView(CheckHasPermissionAPI, generics.UpdateAPIView):
    class InputSerializer(serializers.ModelSerializer):
        class Meta:
            model = FileAnswer
            fields = ['teacher_feedback', 'teacher_audio_feedback', 'essay_was_corrected']
    
    model = FileAnswer
    queryset = FileAnswer.objects.all()
    serializer_class = InputSerializer
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    authentication_classes = (CsrfExemptSessionAuthentication, )