import csv
import json
import os
from pickle import TRUE
import uuid
import io
from fiscallizeon.exams.models import StatusQuestion
from fiscallizeon.questions.models import Question
import pyexcel
from django.http import HttpResponse, JsonResponse
from django_filters.rest_framework import DjangoFilterBackend 
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.filters import SearchFilter

from django.core.cache import cache
from django.db.models import Q, Value, Subquery, OuterRef, Case, When
from django.conf import settings
from django.contrib import messages
from django.urls import reverse
from django.db.models.deletion import ProtectedError

from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from fiscallizeon.core.utils import CheckHasPermission, percentage_formatted
from fiscallizeon.applications.models import Application, ApplicationStudent, ApplicationDeadlineCorrectionResponseException
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.applications.serializers.application_student import ApplicationStudentJustifyDelaySerializer
from fiscallizeon.applications.serializers.application import ApplicationSimpleSerializer, ApplicationSearchSerializer, ApplicationsStudentsCoordinationSerializer, ApplicationDuplicateSerializer, ApplicationDeadlineCorrectionResponseExceptionSerializer, ApplicationCheckExamSimpleSerializer
from fiscallizeon.applications.utils import start_application_student

from django.contrib.auth.mixins import LoginRequiredMixin

from fiscallizeon.students.models import Student
from fiscallizeon.applications.mixins import StudentCanViewResultsMixin
from itertools import groupby


class ApplicationListView(LoginRequiredMixin, CheckHasPermission, generics.ListAPIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    model = Application
    serializer_class = ApplicationSearchSerializer
    queryset = Application.objects.all()
    filter_backends = [SearchFilter, DjangoFilterBackend]
    required_scopes = ['read', 'write']
    search_fields = ['id', 'exam__name']
    filterset_fields = ['date']

    def get_queryset(self):
        
        self.queryset = self.queryset.filter(category=Application.PRESENTIAL, applicationstudent__student__client__in=self.request.user.get_clients_cache()).distinct()
        
        if self.request.GET.get('application_id'): # Coloquei essa condição por que eu preciso que seja esse nome!
            self.queryset = self.queryset.filter(id=self.request.GET.get('application_id'))

        if self.request.GET.get('school_classes'):
            self.queryset = self.queryset.filter(school_classes__in=self.request.GET.getlist('school_classes'))

        if self.request.GET.get('grades'):
            self.queryset = self.queryset.filter(school_classes__grade__in=self.request.GET.getlist('grades'))
        
        return self.queryset

class ApplicationStartView(LoginRequiredMixin, CheckHasPermission, APIView):
    renderer_classes = [JSONRenderer]
    required_permissions = ['student']
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def post(self, request, *args, **kwargs):
        application_student = get_object_or_404(ApplicationStudent, pk=kwargs.get('pk', None))

        response_data = start_application_student(application_student, request)

        if not response_data.get("result", False) == "error":
            return Response(status=status.HTTP_201_CREATED, data=json.dumps(response_data), content_type="application/json")
            
        else:
            return Response(status=status.HTTP_403_FORBIDDEN, data=json.dumps(response_data), content_type="application/json")


class ApplicationFinishView(LoginRequiredMixin, CheckHasPermission, APIView):
    renderer_classes = [JSONRenderer]
    required_permissions = ['student']
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def post(self, request, *args, **kwargs):
        application_student = get_object_or_404(ApplicationStudent, pk=kwargs.get('pk', None))
        empty_questions = request.data.get('empty_questions', 0)

        if application_student.can_be_finished or application_student.application.category == Application.HOMEWORK:
            application_student.end_time = timezone.now().astimezone()
            application_student.empty_questions = empty_questions
            application_student.save()
            return Response(status=status.HTTP_201_CREATED)
        else:
            return Response(status=status.HTTP_403_FORBIDDEN)


class ApplicationCheckFinishView(LoginRequiredMixin, CheckHasPermission, APIView):
    renderer_classes = [JSONRenderer]
    required_permissions = ['student']
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def get(self, request, *args, **kwargs):
        application_student = get_object_or_404(ApplicationStudent, pk=kwargs.get('pk', None))

        return Response(status=status.HTTP_200_OK, data={
            "add_time": application_student.application.end > timezone.localtime(timezone.now()).time(),
            "finish_time": str(application_student.application.date_time_end_tz)
        }, content_type="application/json")
        

class ApplicationsStudentsCoordinationListView(LoginRequiredMixin, CheckHasPermission, generics.ListAPIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    model = Application
    serializer_class = ApplicationsStudentsCoordinationSerializer
    queryset = Application.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {'id': ['in', 'exact']}

    def get_queryset(self):
        self.queryset = self.queryset.filter(
            category=Application.PRESENTIAL,
            exam__coordinations__unity__client__in=self.request.user.get_clients_cache(),
        ).distinct()

        return self.queryset

class ApplicationStudentJustifyDelay(LoginRequiredMixin, CheckHasPermission, generics.UpdateAPIView):
    required_permissions = ['student']
    serializer_class = ApplicationStudentJustifyDelaySerializer
    queryset = ApplicationStudent.objects.all()
    authentication_classes = (CsrfExemptSessionAuthentication, )   

class ApplicationDuplicateDetailView(LoginRequiredMixin, CheckHasPermission, generics.RetrieveUpdateAPIView):
    serializer_class = ApplicationDuplicateSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )
    queryset = Application.objects.all()
    required_permissions = [settings.COORDINATION, ]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        original_application = Application.objects.get(pk=self.kwargs['pk'])
        
        amount = self.request.GET.get('amount')
            
        if amount:
            application_array = []
            for i in range(0, int(amount)):
                duplicate_application = Application.objects.get(pk=instance.pk)
                duplicate_application.pk = uuid.uuid4()
                duplicate_application.duplicate_application = True
                duplicate_application.save()
                application_array.append(duplicate_application)
                
                duplicate_application.inspectors.set(original_application.inspectors.all())
                duplicate_application.students.set(original_application.students.all())
                duplicate_application.school_classes.set(original_application.school_classes.all())
        
            serializer = self.get_serializer(instance = application_array, many = True)
        return Response(serializer.data)
    
class ApplicationChangeIsPrintedAPIView(LoginRequiredMixin, CheckHasPermission, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    required_permissions = [settings.COORDINATION, settings.PARTNER]
    
    def post(self, request, pk):
        application = Application.objects.get(pk=pk)
        if application.exam:
            application.exam.is_printed = not application.exam.is_printed
            application.exam.save(skip_hooks=True)
            print(application.exam.is_printed)
            return Response()
        
        return Response(status=status.HTTP_400_BAD_REQUEST)

class ApplicationChangePrintReadyAPIView(LoginRequiredMixin, CheckHasPermission, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    def post(self, request, pk):
        application = Application.objects.get(pk=pk)
        application.print_ready = not application.print_ready
        application.save(skip_hooks=True)

        return Response()

class ApplicationChangeBookIsPrintedAPIView(LoginRequiredMixin, CheckHasPermission, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    required_permissions = [settings.COORDINATION, settings.PARTNER]
    
    def post(self, request, pk):
        application = Application.objects.get(pk=pk)
        application.book_is_printed = not application.book_is_printed
        application.save(skip_hooks=True)

        return Response()

class ApplicationStudentUploadAPIView(LoginRequiredMixin, CheckHasPermission, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def post(self, request):
        file_obj = request.data.get('file')

        file_path = f'/tmp/tmp-{request.user.pk}.csv'
        with open(file_path, 'wb') as f:
            f.write(file_obj.read())

        with open(file_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=",")
            enrollments = list(reader)
            data = []

            for item in enrollments:
                number = item.get('matriculas')
                students = Student.objects.filter(enrollment_number=number, client__in=request.user.get_clients_cache(), user__is_active=True)
                if students:
                    for student in students:
                        data.append({"id": student.pk, "pk": student.pk, "name": student.name, "classes": student.classes.all().values_list('name', flat=True)})
                
        os.remove(file_path)

        return Response(data)

class ApplicationPagesAmount(LoginRequiredMixin, CheckHasPermission, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    required_permissions = [settings.COORDINATION, settings.PARTNER]

    def post(self, request, pk):
        value = request.data.get('value')
        _type = request.data.get('type')
        application = get_object_or_404(Application, pk=pk)
        
        if _type == 'bag':
            application.bag_pages = value
            application.save(skip_hooks=True)
        else:
            application.book_pages = value
            application.save(skip_hooks=True)
        
        return Response(f"Aplicação {application.exam} atualizada")

def filter_applications_list(self):
    today = timezone.localtime(timezone.now())
    user = self.request.user
    applications = Application.objects.filter(print_ready=True, category=Application.PRESENTIAL, exam__coordinations__unity__client__in=user.get_clients_cache()).order_by('-created_at').distinct()
    
    if self.request.GET.get('year'):
        applications = applications.filter(
            date__year=self.request.GET.get('year'),
        )
    else:
        applications = applications.filter(
            date__year=today.year,
        )

    if self.request.GET.get('q_name', ""):
        applications = applications.filter(
            exam__name__unaccent__icontains=self.request.GET.get('q_name', "")
        )

    if self.request.GET.get('q_unities', ""):
        applications = applications.filter(
            exam__coordinations__unity__in=self.request.GET.getlist('q_unities', "")
        )

    if self.request.GET.get('q_is_printed', ""):
        applications = applications.filter(
            exam__is_printed=True
        )
    if self.request.GET.get('q_book_is_printed', ""):
        applications = applications.filter(
            book_is_printed=True
        )
    if self.request.GET.getlist('q_grades', ""):
        applications = applications.filter(
            exam__teacher_subjects__subject__knowledge_area__grades__pk__in=self.request.GET.getlist('q_grades', "")
            )
    if self.request.GET.getlist('q_systems', ""):
        applications = applications.filter(
            exam__education_system__in=self.request.GET.getlist('q_systems', "")
            )
    return applications
class ApplicationExportPrintList(LoginRequiredMixin, CheckHasPermission, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    required_permissions = [settings.COORDINATION, settings.PARTNER]

    def get(self, request):
        if self.request.GET.get('type') == 'pdf':
            params = ''
            if len(self.request.get_full_path().split('?')) > 1:
                params = self.request.get_full_path().split('?')[1]
            url = f"{reverse('applications:applications_export_pdf')}?{params}"
            return redirect(url)
        
        # export por aplicação
        if self.request.GET.get('type') == 'application':
            buffer = io.StringIO()
            wr = csv.writer(buffer, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
            csv_header = ['Sistema de ensino', 'Nome do caderno', 'Numero de Alunos', 'Disciplina', 'Sigla', 'folhas no malote', 'folhas no caderno']
            wr.writerow(csv_header)

            for application in filter_applications_list(self):
                application_row = []
                subjects = application.exam.get_initials_subjects()
                application_row.append(application.exam.education_system if application.exam.education_system else '-')
                application_row.append(application.exam.name)
                application_row.append(ApplicationStudent.objects.filter(application=application.pk).count())
                application_row.append(subjects[0]['name'] if subjects else "-")
                application_row.append(subjects[0]['initial'] if subjects else "-")
                application_row.append(application.bag_pages)
                application_row.append(application.book_pages)

                wr.writerow(application_row)
            
            buffer.seek(0)
            sheet = pyexcel.load_from_memory("csv", buffer.getvalue())

            response = HttpResponse(sheet.csv, content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="exportação.csv"'
            return response

        # export por turma
        buffer = io.StringIO()
        wr = csv.writer(buffer, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
        csv_header = ['Nome do caderno', 'Sistema', 'Unidade', 'Serie', 'Turma', 'Disciplina', 'Sigla', 'Numero de Alunos', 'Check']

        wr.writerow(csv_header)

        for application in filter_applications_list(self):
            for _class in application.get_classes():
                class_row = []
                subjects = application.exam.get_initials_subjects()
                class_row.append(application.exam.name)
                class_row.append(application.exam.education_system if application.exam.education_system else '-')
                class_row.append(_class['coordination__unity__name'])
                class_row.append(_class['name'][:2])
                class_row.append(_class['name'])
                class_row.append(subjects[0]['name'] if subjects else "-")
                class_row.append(subjects[0]['initial'] if subjects else "-")
                class_row.append(_class['students_count'])

                wr.writerow(class_row)
        
        buffer.seek(0)
        sheet = pyexcel.load_from_memory("csv", buffer.getvalue())

        response = HttpResponse(sheet.csv, content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="exportação.csv"'
        return response


class ApplicationDeadlineCorrectionResponseExceptionCreateDeleteAPIView(generics.CreateAPIView, generics.DestroyAPIView):
    serializer_class = ApplicationDeadlineCorrectionResponseExceptionSerializer
    authentication_classes = (CsrfExemptSessionAuthentication,)

    def get_queryset(self):
        return ApplicationDeadlineCorrectionResponseException.objects.filter(
            application_id=self.kwargs.get('application_id')
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, many=isinstance(request.data, list))
        serializer.is_valid(raise_exception=True)

        ApplicationDeadlineCorrectionResponseException.objects.filter(
            application_id=self.kwargs.get('application_id')
        ).delete()

        ApplicationDeadlineCorrectionResponseException.objects.bulk_create(
            [
                ApplicationDeadlineCorrectionResponseException(
                    **application_deadline_correction_response_exception,
                    application_id=self.kwargs.get('application_id'),
                )
                for application_deadline_correction_response_exception in serializer.validated_data
            ]
        )
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

class ApplicationCheckExamView(LoginRequiredMixin, CheckHasPermission, APIView):
    required_permissions = [settings.COORDINATION, settings.PARTNER]
    model = Application
    serializer_class = ApplicationCheckExamSimpleSerializer
    
    def get(self, request, *args, **kwargs):
        exam_id = kwargs.get('pk')
        applications = Application.objects.filter(exam_id=exam_id)

        if applications.exists():
            serializer = self.serializer_class(applications, many=True)
            return JsonResponse({'exist': True, 'applications': serializer.data})
        else:
            return JsonResponse({'exist': False, 'error': 'No applications found for this exam_id'})

class ApplicationDeleteAPIView(generics.DestroyAPIView):
    queryset = Application.objects.all()
    serializer_class = ApplicationSimpleSerializer  

    def delete(self, request, *args, **kwargs):
        application = self.get_object()
        user = request.user

        if not user.is_authenticated or (user.user_type == settings.TEACHER and 
                                        (not application.exam.created_by == user or 
                                        not user.client_teachers_can_elaborate_exam)):
            messages.error(self.request, 'Você não tem permissão para remover esta aplicação')
            return Response({'error': 'Você não tem permissão para remover esta aplicação'}, status=status.HTTP_403_FORBIDDEN)

        try:
            application.delete()
            return JsonResponse({'message': 'OK'}, status=200)

        except ProtectedError:
            messages.error(self.request, "Ocorreu um erro ao remover, não é possível remover aplicações que houve participação de alunos.")
            return JsonResponse({'error': 'Ocorreu um erro ao remover, não é possível remover aplicações que houve participação de alunos.'}, status=400)

class ApplicationTokenOnlineView(LoginRequiredMixin, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def get(self, request, pk):
        user_already_response_token = request.session.get(f'token_from_application_{pk}', False)
        
        return JsonResponse({
            "already_response": user_already_response_token,
        }, status=200)

    def post(self, request, pk):

        application_instance = Application.objects.get(pk=pk)
        application_student_pk = request.data.get('application_student_pk')
        token = request.data.get('token')

        if application_instance.token_online:
            if application_instance.token_online == token:

                request.session[f'token_from_application_{pk}'] = True
                application_student = ApplicationStudent.objects.get(pk=application_student_pk)
                url = reverse('applications:applications_monitoring_student', kwargs={'pk': application_student.pk})
                
                return JsonResponse({
                    "url_application": url,
                }, status=200)
            else:
                return JsonResponse({
                    "error": "Token incorreto para essa aplicação",
                },status=400)
            
        else:
            return JsonResponse({'error': 'Token online não configurado para essa aplicação'}, status=400)        

class TeacherSubjectListFromApplication(LoginRequiredMixin, StudentCanViewResultsMixin, APIView):
    # View criada para a tela de detalhes de aplicação do aluno, substitui a consulta que era feita no contexto

    authentication_classes = (CsrfExemptSessionAuthentication,)

    def get_object(self):
        return get_object_or_404(ApplicationStudent.objects.all(), pk=self.kwargs.get('pk'))  

    def get(self, request, pk):
        application_student = self.get_object()
        applications_student = ApplicationStudent.objects.filter(pk=pk)

        exam = application_student.application.exam
        exam_questions = exam.examquestion_set.all()
        is_enem_simulator = exam.is_enem_simulator
        
        CACHE_KEY = f'APPLICATION_STUDENT_RESULTS_EXAMTEACHER_SUBJECTS_{application_student.id}'
        
        if exam.is_abstract:

            if not cache.get(CACHE_KEY):

                exam = application_student.application.exam
                exam_questions = list(exam.examquestion_set.all())
                exam_questions.sort(key=lambda eq: eq.question.subject.pk)

                subjects = []

                for subject_pk, group in groupby(exam_questions, key=lambda eq: eq.question.subject.pk):
                    questions_list = list(group)
                    first_exam_question = questions_list[0]
                    subject = first_exam_question.question.subject

                    details = applications_student.get_annotation_count_answers(subjects=[subject], exclude_annuleds=True, only_total_answers=True).first()

                    subjects.append({
                        "subject": subject.name,
                        "subject_id": str(subject.id),
                        "knowledge_area": subject.knowledge_area.name if subject.knowledge_area.name else "Sem área de conhecimento",
                        "examquestions_count": len(questions_list),
                        "correct_count": details.total_correct_answers,
                        "incorrect_count": details.total_incorrect_answers,
                        "partial_count": details.total_partial_answers,
                        "score": application_student.get_total_grade(subject=subject) if not is_enem_simulator else 0,
                        "performance": percentage_formatted(application_student.get_performance_v2(subject=subject)),
                        "total_weight": exam.get_total_weight(extra_filters=Q(exam_teacher_subject__teacher_subject__subject=subject)),
                    })
                
                cache.set(CACHE_KEY, subjects, 60)
                
            else:
                subjects = cache.get(CACHE_KEY)

        else:
            
            this_exam_teacher_subjects = exam.examteachersubject_set
            
            examteacher_subjects = this_exam_teacher_subjects.select_related('teacher_subject', 'teacher_subject__subject').order_by().distinct('teacher_subject__subject')

            if examteacher_subjects.filter(is_foreign_language=True).exists():

                foreign_language_options = this_exam_teacher_subjects.filter(is_foreign_language=True).order_by('order')
                first_option = foreign_language_options.first()
                last_option = foreign_language_options.last() 

                if application_student.foreign_language == ApplicationStudent.ENGLISH:
                    examteacher_subjects = examteacher_subjects.exclude(pk=last_option.pk)
                else:
                    examteacher_subjects = examteacher_subjects.exclude(pk=first_option.pk)



            subjects = []
            if not cache.get(CACHE_KEY):

                for exam_teacher_subject in examteacher_subjects:

                    details = applications_student.get_annotation_count_answers(subjects=[exam_teacher_subject.teacher_subject.subject], exclude_annuleds=True, only_total_answers=True).first()

                    subjects.append({
                        "subject": exam_teacher_subject.teacher_subject.subject.name,
                        "subject_id": exam_teacher_subject.teacher_subject.subject.id,
                        "knowledge_area": exam_teacher_subject.teacher_subject.subject.knowledge_area.name if exam_teacher_subject.teacher_subject.subject.knowledge_area else "Sem disciplina",
                        "examquestions_count": exam_questions.filter(
                            exam_teacher_subject__teacher_subject__subject=exam_teacher_subject.teacher_subject.subject
                        ).distinct().availables().count(),
                        "correct_count": details.total_correct_answers,
                        "incorrect_count": details.total_incorrect_answers,
                        "partial_count": details.total_partial_answers,
                        "score": application_student.get_total_grade(subject=exam_teacher_subject.teacher_subject.subject) if not is_enem_simulator else 0,
                        "performance": percentage_formatted(application_student.get_performance_v2(subject=exam_teacher_subject.teacher_subject.subject)),
                        "total_weight": exam.get_total_weight(extra_filters=Q(exam_teacher_subject__teacher_subject__subject=exam_teacher_subject.teacher_subject.subject)),
                    })

                cache.set(CACHE_KEY, subjects, 60)
            else:
                subjects = cache.get(CACHE_KEY)

        return JsonResponse(status=status.HTTP_200_OK, data=subjects, safe=False)

class QuestionsReportFromApplication(LoginRequiredMixin, StudentCanViewResultsMixin, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication,)
    
    def get_object(self):
        return get_object_or_404(ApplicationStudent.objects.all(), pk=self.kwargs.get('pk'))    

    def get(self, request, pk):
        application_student = self.get_object()
        exam = application_student.application.exam
        questions_to_exclude = None
        CACHE_KEY = f'APPLICATION_STUDENT_RESULTS_QUESTIONS_{application_student.pk}'

        # Código para encontrar as questions da disciplina estrangeira não escolhida pelo aluno, e excluir elas 
        this_exam_teacher_subject = exam.examteachersubject_set
        if this_exam_teacher_subject.filter(is_foreign_language=True).exists():

            foreign_language_options = this_exam_teacher_subject.filter(is_foreign_language=True).order_by('order')
            first_option = foreign_language_options.first()
            last_option = foreign_language_options.last() 
            
            if application_student.foreign_language == ApplicationStudent.ENGLISH:
                questions_to_exclude = [examquestion.question.pk for examquestion in last_option.examquestion_set.all()]
            else:
                questions_to_exclude = [examquestion.question.pk for examquestion in first_option.examquestion_set.all()]
        
        if not cache.get(CACHE_KEY):
            questions = (
                Question.objects.availables(exam)
                .select_related('subject', 'subject__knowledge_area','grade')
                .get_application_student_report(application_student, only_answers=True)
                .order_by(
                    'examquestion__exam_teacher_subject__order', 'examquestion__order'
                ).annotate(
                    last_status=Subquery(
                        StatusQuestion.objects.filter(
                            active=True, 
                            exam_question__question=OuterRef('pk'), 
                            exam_question__exam=exam
                        ).order_by('-created_at').values('status')[:1]),
                    give_score=Subquery(
                        StatusQuestion.objects.filter(
                            active=True,
                            exam_question__question=OuterRef('pk'),
                            exam_question__exam=exam,
                            annuled_give_score=True
                        ).order_by('-created_at').values('annuled_give_score')[:1]
                    ),
                    annuled=Case(
                        When(
                            Q(last_status=StatusQuestion.ANNULLED),
                            then=Value(True)
                        ), default=Value(False)
                    )
                )
            )

            if questions_to_exclude:
                questions = questions.exclude(
                    pk__in=questions_to_exclude
                )
            cache.set(CACHE_KEY, questions, 60)
        else:
            questions = cache.get(CACHE_KEY)
        
        # dados das questões
        questions_data = []
        for question in questions:
            question_data = {}
            question_data['number_print'] = exam.number_print_question(question)
            question_data['id'] = question.pk
            question_data['give_score'] = question.give_score
            question_data['annuled'] = question.annuled
            question_data['percent_grade'] = question.percent_grade
            question_data['teacher_grade'] = question.teacher_grade
            question_data['is_correct'] = question.is_correct
            question_data['is_incorrect'] = question.is_incorrect
            question_data['is_partial'] = question.is_partial
            question_data['category'] = question.category
            
            questions_data.append(question_data)
        
        # dados da aplicação
        questions_count = questions.count()
        questions_without_annuleds = questions.availables(exam, exclude_annuleds=True)
        correct_count = questions_without_annuleds.filter(is_correct=True).distinct().count()
        partial_count = questions_without_annuleds.filter(is_partial=True).count()
        incorrect_count = questions_without_annuleds.filter(is_incorrect=True).count()
        
        
        application_data = {
            "questions_data": questions_data,
            "correct_count": correct_count,
            "partial_count": partial_count,
            "incorrect_count": incorrect_count,
            "questions_count": questions_count,
        }
            
        return JsonResponse(status=status.HTTP_200_OK, data=application_data, safe=False)

application_exam_exist = ApplicationCheckExamView.as_view()
application_list = ApplicationListView.as_view()
application_start_view = ApplicationStartView.as_view()
application_end_view = ApplicationFinishView.as_view()
application_check_end_view = ApplicationCheckFinishView.as_view()
application_duplicate = ApplicationDuplicateDetailView.as_view()
application_delete_api= ApplicationDeleteAPIView.as_view()
application_token_online = ApplicationTokenOnlineView.as_view()

application_student_justify_delay = ApplicationStudentJustifyDelay.as_view()

applications_students_coordination = ApplicationsStudentsCoordinationListView.as_view()

application_student_upload = ApplicationStudentUploadAPIView.as_view()

application_pages_amount = ApplicationPagesAmount.as_view()
export_print_list = ApplicationExportPrintList.as_view()

teacher_subject_list_from_application = TeacherSubjectListFromApplication.as_view()
questions_report_from_application = QuestionsReportFromApplication.as_view()