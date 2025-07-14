from django.http import Http404
from rest_framework import generics, permissions

from fiscallizeon.answers.serializers.textual_answers import TextualAnswerRemoveGradeSerializer, TextualAnswerCreateFeedbackSerializer, TextualAnswerSerializer, TextualAnswerFeedbackSerializer
from fiscallizeon.answers.models import TextualAnswer
from fiscallizeon.answers.permissions import IsOwner
from fiscallizeon.exams.permissions import IsTeacherSubject

from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.core.utils import CheckHasPermissionAPI
import logging


logger = logging.getLogger()


class TextualAnswerCreateView(generics.CreateAPIView):
    model = TextualAnswer
    serializer_class = TextualAnswerSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )
    permission_classes = [IsOwner]


class TextualAnswerRetreiveUpdateView(generics.RetrieveUpdateAPIView):
    model = TextualAnswer
    serializer_class = TextualAnswerSerializer
    queryset = TextualAnswer.objects.all()
    permission_classes = [IsOwner]
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    
class TextualAnswerRemoveGradeUpdateView(CheckHasPermissionAPI, generics.UpdateAPIView):
    serializer_class = TextualAnswerRemoveGradeSerializer
    queryset = TextualAnswer.objects.all()
    authentication_classes = (CsrfExemptSessionAuthentication, )
    

class TextualAnswerFeedbackUpdateView(generics.UpdateAPIView):
    model = TextualAnswer
    serializer_class = TextualAnswerFeedbackSerializer
    queryset = TextualAnswer.objects.all()
    permission_classes = [IsTeacherSubject]
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    def get_object(self):
        question_id = self.request.data.get("question", None)
        student_application_id = self.request.data.get("student_application", None)
        try:
            textual_answer = TextualAnswer.objects.using('default').filter(pk=self.kwargs['pk']).first() or TextualAnswer.objects.using('default').filter(question=question_id, student_application=student_application_id).first()
            if textual_answer:
                return textual_answer
            raise Http404
        except Http404:
            obj = TextualAnswerCreateFeedbackSerializer(data=self.request.data)
            obj.is_valid(raise_exception=True)
            obj.save(corrected_but_no_answer=True)
            return obj.instance
        except Exception as e:
            return e

class TextualAnswerDeleteAnswerDeleteAPIView(CheckHasPermissionAPI, generics.DestroyAPIView):
    queryset = TextualAnswer.objects.all()
    authentication_classes = (CsrfExemptSessionAuthentication, )