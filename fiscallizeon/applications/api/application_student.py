from django.conf import settings
from rest_framework.generics import RetrieveAPIView, UpdateAPIView
from rest_framework.views import APIView
from fiscallizeon.core.utils import CheckHasPermissionAPI
from fiscallizeon.core.api.csrf_exempt_session import CsrfExemptSessionAuthentication
from rest_framework.response import Response
from django.contrib.auth.mixins import LoginRequiredMixin

from fiscallizeon.applications.models import ApplicationStudent
from rest_framework import serializers
from fiscallizeon.applications.serializers.application_student_exam import ApplicationStudentExamSerializer
from fiscallizeon.applications.permissions import IsStudentOwner, IsCoordinationMember, IsCoordinationMemberCanSeeAll, IsTeacherSubject
from fiscallizeon.answers.models import OptionAnswer
from fiscallizeon.analytics.models import GenericPerformancesFollowUp
from fiscallizeon.applications.models import Application
from django.db.models import F
from django.db.models.functions import TruncDate, TruncTime
from django.utils import timezone

from datetime import datetime, time

class ApplicationStudentExamDetails(LoginRequiredMixin, RetrieveAPIView):
    serializer_class = ApplicationStudentExamSerializer
    queryset = ApplicationStudent.objects.all()
    permission_classes = [IsCoordinationMemberCanSeeAll|IsCoordinationMember|IsStudentOwner|IsTeacherSubject]
    model = ApplicationStudent



class ApplicationStudentClearUpdateAPIView(LoginRequiredMixin, CheckHasPermissionAPI, UpdateAPIView):
    class InputSerializer(serializers.ModelSerializer):
        class Meta:
            model = ApplicationStudent
            fields = ['feedback_after_clean', 'missed']
            ref_name = 'applicationstudent_clear'
            
    authentication_classes = (CsrfExemptSessionAuthentication, )
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    serializer_class = InputSerializer
    queryset = ApplicationStudent.objects.all()
    
    def perform_update(self, serializer):
        from fiscallizeon.analytics.models import GenericPerformancesFollowUp
        
        application_student = serializer.save()
        
        examquestions = application_student.application.exam.examquestion_set.filter(weight__gt=0).availables(exclude_annuleds=True)
        
        operation_type = 'remove' if application_student.missed else 'add'
        
        options = application_student.option_answers.all()
        textuals = application_student.textual_answers.all()
        files = application_student.file_answers.all()
        sums = application_student.sum_answers.all()
        
        questions_pks = options.filter(status=OptionAnswer.ACTIVE).annotate(question__pk=F('question_option__question__pk')).values('question__pk').union(textuals.filter(empty=False).values('question__pk')).union(files.filter(empty=False).values('question__pk')).union(sums.filter(empty=False).values('question__pk'))
        
        if self.request.GET.get('clean_answers'):
            
            filtred_examquestions = examquestions.filter(question__in=questions_pks.values('question__pk'))
            operation_type = 'add'
            options.delete()
            textuals = textuals.update(teacher_grade=None, corrected_but_no_answer=False, who_corrected=None)
            files = files.update(teacher_grade=None, corrected_but_no_answer=False, who_corrected=None)
            sums = sums.update(grade=None)
        
        else:
            filtred_examquestions = examquestions.exclude(question__in=questions_pks.values('question__pk'))
            
        for examquestion in filtred_examquestions:
            GenericPerformancesFollowUp.update_answer_quantity(question_id=examquestion.question.id, application_student=application_student, operation_type=operation_type)
        
class ApplicationStudentEmptyQuestionsAPIView(LoginRequiredMixin, CheckHasPermissionAPI, APIView):
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def post(self, request, pk=None):
        
        data = request.data
        
        question_id = data.get('question_id')
        
        application_student = ApplicationStudent.objects.get(pk=pk)
        
        application_student.empty_option_questions.add(question_id)
        
        try:
            option_answers = OptionAnswer.objects.filter(student_application=application_student, question_option__question=question_id)
            if option_answer := option_answers.filter(status=OptionAnswer.ACTIVE).first():
                option_answer.delete()
                
        except Exception as e:
            print("Erro ao tentar adicionar questão como em branco na applicationstudent", e)
        
        return Response(application_student.empty_option_questions.using('default').all().values_list('pk', flat=True))
        

class ApplicationStudentChooseLanguageUpdateAPIView(LoginRequiredMixin, CheckHasPermissionAPI, UpdateAPIView):
    class InputSerializer(serializers.ModelSerializer):
        class Meta:
            model = ApplicationStudent
            fields = ['foreign_language']
            ref_name = 'application_student_choose_language'
            
    authentication_classes = (CsrfExemptSessionAuthentication, )
    required_permissions = [settings.STUDENT]
    serializer_class = InputSerializer
    queryset = ApplicationStudent.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        user = self.request.user
        
        queryset = queryset.filter(student__user=user)
        return queryset
    

application_student_exam_api = ApplicationStudentExamDetails.as_view()

class ApplicationStudentExceptionApiView(LoginRequiredMixin, CheckHasPermissionAPI, APIView):

    required_permissions = [settings.COORDINATION, settings.TEACHER]
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def get(self, request, pk=None):

        application_pk = self.request.GET.get('application')
        application_instance = Application.objects.get(pk=application_pk)

        applications_students = application_instance.applicationstudent_set.filter(
            custom_time_finish__isnull=False
        ).annotate(
            date=TruncDate('custom_time_finish'),
            time=TruncTime('custom_time_finish')
        )
        
        return Response({
            "applications_students": applications_students.values('id','date','time','student__name'),
        },200)

    def post(self, request, pk=None):

        data = request.data
        category = data.get('category') # Categoria selecionada vem no payload porque essa função pode rodar antes de atualizar o application
        students_data = data.get('students_data')

        applications_students = ApplicationStudent.objects.filter(pk__in=[student['id'] for student in students_data])

        student_stats_permission_date = applications_students.first().application.student_stats_permission_date

        for student in students_data:
            
            application_student = applications_students.get(pk=student['id'])

            date_value = application_student.application.date if category == 2 else student['date']
            
            try:
                time_value = time.fromisoformat(student['time']+':00') # Adiciona os segundos caso não tenha
            except ValueError:
                time_value = time.fromisoformat(student['time'])

            custom_time_finish = datetime.strptime(f"{date_value} {time_value}", "%Y-%m-%d %H:%M:%S")
            custom_time_finish = timezone.make_aware(custom_time_finish) if timezone.is_naive(custom_time_finish) else custom_time_finish # Adiciona timezone se não tiver

            if student_stats_permission_date and custom_time_finish > student_stats_permission_date:
                return Response({
                    "student_id": student['id'],
                    "error": f"O tempo é maior que a data de liberação de resultados dessa aplicação."
                }, status=400)

            application_student.custom_time_finish = custom_time_finish
            application_student.start_time = None # Limpa o start_time para não ter conflito com o custom_time_finish
                
            application_student.save()

        
        return Response({},status=200)
    
    def delete(self, request, pk=None):
        
        application_student = ApplicationStudent.objects.get(pk=self.request.GET.get('applicationstudent'))

        application_student.custom_time_finish = None
        application_student.save()
        
        return Response({
            "success": True
        },status=201)
    
application_student_exception_api = ApplicationStudentExceptionApiView.as_view()