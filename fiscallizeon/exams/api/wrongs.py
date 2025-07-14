from django.utils import timezone
from django.conf import settings
from rest_framework.generics import RetrieveUpdateAPIView, CreateAPIView, ListAPIView, UpdateAPIView
from fiscallizeon.answers.models import FileAnswer, TextualAnswer
from fiscallizeon.answers.serializers.option_answers import QuestionOptionAnswerVerySimpleSerializer
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.core.api.csrf_exempt_session import CsrfExemptSessionAuthentication
from fiscallizeon.exams.models import ExamQuestion, Wrong
from fiscallizeon.exams.serializers.wrongs import StudentWrongResendSerializerUpdate, WrongSerializer, WrongSerializerCreate

from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.response import Response
from rest_framework import status

from fiscallizeon.questions.models import QuestionOption




class StudentCorreccionContestationListAPIView(LoginRequiredMixin, ListAPIView):
    queryset = Wrong.objects.all()
    serializer_class = WrongSerializer
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    authentication_classes = [CsrfExemptSessionAuthentication]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['student'] = self.request.GET.get('student', '')
        return context
        
    def get_queryset(self):
        
        queryset = Wrong.objects.filter(student__client__in=self.request.user.get_clients_cache())

        if self.request.GET.get('application_student') and self.request.GET.get('question'):
            application_student = ApplicationStudent.objects.get(pk=self.request.GET.get('application_student'))
            exam_question = ExamQuestion.objects.get(
                exam=application_student.application.exam, question=self.request.GET.get('question')
            )
            queryset  = Wrong.objects.filter(
                student=self.request.user.student,
                exam_question=exam_question
            )

        return queryset

class StudentCorreccionContestationCreateAPIView(LoginRequiredMixin, CreateAPIView):
    queryset = Wrong.objects.all()
    serializer_class = WrongSerializerCreate    
    authentication_classes = [CsrfExemptSessionAuthentication]    

    def create(self, request, *args, **kwargs):
        data = request.data
        application_student = ApplicationStudent.objects.get(pk=data.get('application_student'))
        exam_question = ExamQuestion.objects.get(exam=application_student.application.exam, question=data.get('question'))
        
        data['student'] = application_student.student.pk
        data['exam_question'] = exam_question.pk

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class StudentCorreccionContestationRetrieveUpdateAPIView(LoginRequiredMixin, RetrieveUpdateAPIView):
    queryset = Wrong.objects.all()
    serializer_class = WrongSerializer
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    authentication_classes = [CsrfExemptSessionAuthentication]

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['student'] = self.request.GET.get('student', '')

        return context

    def perform_update(self, serializer):
        serializer.save(user=self.request.user, response_date=timezone.now())

        selected_answer = self.request.data.get('selected_answer')
        if selected_answer:
            if selected_answer.get('arquivo'):
                FileAnswer.objects.filter(pk=selected_answer.get('id')).update(teacher_grade=selected_answer.get('teacher_grade'))
                
            if selected_answer.get('content'):
                TextualAnswer.objects.filter(pk=selected_answer.get('id')).update(teacher_grade=selected_answer.get('teacher_grade'))


class StudentCorreccionContestationResendUpdateAPIView(LoginRequiredMixin, UpdateAPIView):
    queryset = Wrong.objects.all()
    serializer_class = StudentWrongResendSerializerUpdate
    required_permissions = [settings.STUDENT]
    authentication_classes = [CsrfExemptSessionAuthentication]

    def perform_update(self, serializer):
        serializer.save(status=Wrong.AWAITING_REVIEW, updated_at=timezone.now())


class WrongChangeQuestionOptionAnswer(LoginRequiredMixin, UpdateAPIView):
    queryset = QuestionOption.objects.all()
    serializer_class = QuestionOptionAnswerVerySimpleSerializer
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    authentication_classes = [CsrfExemptSessionAuthentication]

    def perform_update(self, serializer):
        serializer.save()

student_correccion_contestation_list = StudentCorreccionContestationListAPIView.as_view()
student_correccion_contestation_create = StudentCorreccionContestationCreateAPIView.as_view()
student_correccion_contestation_retrieve_update = StudentCorreccionContestationRetrieveUpdateAPIView.as_view()
student_correccion_contestation_resend_update = StudentCorreccionContestationResendUpdateAPIView.as_view()

wrongs_change_option_answer = WrongChangeQuestionOptionAnswer.as_view()