from rest_framework import permissions
from rest_framework.generics import ListCreateAPIView, RetrieveAPIView, RetrieveUpdateDestroyAPIView
from fiscallizeon.analytics.api.serializers.base_texts import BaseTextExamSerializer, BaseTextSerializer
from fiscallizeon.exams.models import Exam
from fiscallizeon.questions.models import BaseText, Question
from rest_framework.authentication import BasicAuthentication
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings

class BaseTextListCreateAPIView(ListCreateAPIView):
    queryset = BaseText.objects.all()
    serializer_class = BaseTextSerializer
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    authentication_classes = (CsrfExemptSessionAuthentication, )
    search_fields = ('title', )
    ordering_fields = ('-created_at', )

    def get_queryset(self):
        queryset = super(BaseTextListCreateAPIView, self).get_queryset()
        queryset = queryset.filter(created_by=self.request.user).order_by('-created_at')
        
        if self.request.GET.get('search'):
            return queryset

        return queryset[:10]

        
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
          
class BaseTextRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    queryset = BaseText.objects.all() 
    serializer_class = BaseTextSerializer
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    authentication_classes = (CsrfExemptSessionAuthentication, )  
    
    def destroy(self, request, *args, **kwargs):
        question_base_texts = Question.objects.filter(base_texts=self.get_object())
        if not question_base_texts:
            self.get_object().delete()
            return Response(data={'Success':"Deleted Successfully."}, status=status.HTTP_200_OK)
        
        return Response(data={'Error': "Did not delete."}, status=status.HTTP_423_LOCKED)
             
class BaseTextExamRetrieveAPIView(RetrieveAPIView):
    queryset = Exam.objects.all()
    serializer_class = BaseTextExamSerializer
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    authentication_classes = (CsrfExemptSessionAuthentication, )
    permission_classes = [permissions.AllowAny]
    

base_text_list_create = BaseTextListCreateAPIView.as_view()
base_text_retrive_update_destroy = BaseTextRetrieveUpdateDestroyAPIView.as_view()
base_text_exam = BaseTextExamRetrieveAPIView.as_view()