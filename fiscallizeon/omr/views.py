import os
import re
import logging
import itertools
import shutil
import datetime
from io import BytesIO
from functools import reduce
from django.utils.translation import activate
from celery.result import AsyncResult
from sentry_sdk import capture_message
from pikepdf import Pdf, Page, Rectangle
import qrcode.image.svg #NÃO REMOVER ESSA LINHA, MESMO QUE NÃO ESTEJA SENDO USADA EM ALGUMA VIEW

from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Case, When
from django.db.models.functions import Cast, Coalesce
from django.db.models.aggregates import Count
from django.db.models.deletion import ProtectedError
from django.db.models.expressions import F
from django.db.models import Subquery, OuterRef, Exists

from django.db.models.query_utils import Q
from django.utils import formats, timezone
from django.urls import reverse
from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.views.generic.base import RedirectView, TemplateView
from django.views.generic.edit import DeleteView, FormView, UpdateView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages

from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from fiscallizeon.celery import app
from fiscallizeon.clients.models import Client, QuestionTag, Unity, CoordinationMember, TeachingStage
from fiscallizeon.students.models import Student
from fiscallizeon.core.gcp.utils import get_service_account_oauth2_token
from fiscallizeon.core.requests_utils import get_session_retry
from fiscallizeon.classes.models import Grade, SchoolClass
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.accounts.mixins import LoginOrTokenRequiredMixin
from fiscallizeon.applications.models import Application, ApplicationStudent, RandomizationVersion
from fiscallizeon.exams.forms import ExamForm
from fiscallizeon.questions.models import Question
from fiscallizeon.subjects.models import Subject
from fiscallizeon.exams.models import Exam, ExamHeader, ExamQuestion, ExamTeacherSubject
from fiscallizeon.exams.json_utils import get_exam_base_json, convert_json_to_choice_exam_questions_list
from fiscallizeon.omr.forms import AnswerSheetForm, OffsetSchoolClassAnswerSheetForm, OMRErrorFormSet, OMRDiscursiveErrorFormSet
from fiscallizeon.omr.tasks import proccess_sheets
from fiscallizeon.omr.tasks.reprocessing.reproccess_sheets import reproccess_sheets
from fiscallizeon.omr.tasks.salta.reproccess_sheets_salta import reproccess_sheets_salta
from fiscallizeon.omr.tasks.elit.reproccess_sheets_elit import reproccess_sheets_elit
from fiscallizeon.omr.tasks.sesi.reproccess_sheets_sesi import reproccess_sheets_sesi
from fiscallizeon.omr.tasks.reprocessing.reproccess_discursive_questions import reproccess_discursive_questions
from fiscallizeon.omr.tasks.olimpiada_rio.proccess_sheets_rio import proccess_sheets_rio
from fiscallizeon.omr.tasks.eleva.proccess_sheets_eleva import proccess_sheets_eleva
from fiscallizeon.omr.tasks.salta.proccess_sheets_salta import proccess_sheets_salta
from fiscallizeon.omr.tasks.elit.process_elit_sheets import process_elit_sheets
from fiscallizeon.omr.tasks.sesi.proccess_sheets_sesi import proccess_sheets_sesi
from fiscallizeon.omr.tasks.offset_schoolclass.proccess_sheets_offset import proccess_sheets_offset
from fiscallizeon.omr.models import OMRUpload, OMRCategory, OMRStudents, OMRDiscursiveError, OMRError
from fiscallizeon.omr.utils import get_qr_code
from fiscallizeon.omr.serializers.omr_upload import AnswerSheetSerializer
from fiscallizeon.subjects.models import KnowledgeArea, Subject, SubjectRelation
from fiscallizeon.distribution.utils import merge_memory_pdfs

from fiscallizeon.notifications.models import Notification
from fiscallizeon.notifications.functions import get_and_create_notifications

class PrintApplicationStudentAnswerSheetView(LoginOrTokenRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = [settings.COORDINATION, ]
    model = ApplicationStudent
    is_enem = False
    is_hybrid = False

    def get_object(self):
        return ApplicationStudent.objects.using('default').get(pk=self.kwargs.get('pk'))

    def dispatch(self, request, *args, **kwargs):
        self.is_enem = bool(request.GET.get('enem', 0))
        self.is_hybrid = bool(request.GET.get('hybrid', 0))
        self.is_sum = bool(request.GET.get('sum', 0))
        self.is_subjects = bool(request.GET.get('subjects', 0))
        self.is_reduced = bool(request.GET.get('reduced', 0))
        self.version_number = request.GET.get('randomization_version', None)
        return super(PrintApplicationStudentAnswerSheetView, self).dispatch(request, *args, **kwargs)

    def get_template_names(self):
        if self.is_enem:
            return ['omr/export_answer_sheets_enem_new.html']
        elif self.is_hybrid:
            return ['omr/export_answer_sheets_hybrid.html']
        elif self.is_sum:
            return ['omr/mockups/answer_sheet_sum.html']
        elif self.is_subjects:
            return ['omr/mockups/answer_sheet_subjects.html']
        elif self.is_reduced:
            return ['omr/mockups/answer_sheet_reduced_model.html']
        return ['omr/export_answer_sheets.html']

    def get_context_data(self, **kwargs):
        context = super(PrintApplicationStudentAnswerSheetView, self).get_context_data(**kwargs)

        randomization_version = None
        if self.version_number:
            randomization_version = RandomizationVersion.objects.filter(
                application_student=self.object,
                version_number=self.version_number,
            ).first()

        exam = self.object.application.exam
        is_randomized = bool(randomization_version)

        sequential = OMRCategory.FISCALLIZE
        if self.is_enem:
            sequential = OMRCategory.ENEM
        elif self.is_hybrid:
            sequential = OMRCategory.HYBRID_025
        elif self.is_sum:
            sequential = OMRCategory.SUM_1
        elif self.is_subjects:
            sequential = OMRCategory.SUBJECTS_1
        elif self.is_reduced:
            sequential = OMRCategory.REDUCED_MODEL

        self.object.qr_code = get_qr_code(
            self.object.pk, 
            sequential,
            f'R{self.version_number}' if is_randomized else 'S'
        )
        qr_code_text = '{}:{}:{}'.format(
            f'R{self.version_number}' if is_randomized else 'S',
            sequential,
            self.object.pk
        )

        self.object.school_class = self.object.get_last_class_student()

        exam_questions = ExamQuestion.objects.filter(
            exam=exam,
            question__number_is_hidden=False,
        ).availables().order_by(
            'exam_teacher_subject__order', 'order'
        )

        if self.is_subjects:
            exam_questions = exam_questions.filter(
                question__category=Question.CHOICE,
            ).order_by()

            if self.object.application.exam.is_abstract:
                exam_questions = exam_questions.annotate(
                    subject=F('question__subject__name')
                ).order_by('order')
            else:
                exam_json = get_exam_base_json(self.object.application.exam)
                exam_questions_list = convert_json_to_choice_exam_questions_list(exam_json)
                exam_questions_pks = [q['pk'] for q in exam_questions_list]

                exam_questions = exam_questions.get_ordered_pks(
                    exam_questions_pks
                ).annotate(
                    subject=F('exam_teacher_subject__teacher_subject__subject__name')
                )

        elif exam.has_foreign_languages:
            if exam.is_abstract:
                questions = exam.get_foreign_exam_questions()
                last_foreign_language_questions = questions[questions.count()//2:]
            elif foreign_subjects := exam.get_foreign_exam_teacher_subjects():
                last_foreign_language_questions = foreign_subjects[1].examquestion_set.availables()

            exam_questions = exam_questions.exclude(
                pk__in=last_foreign_language_questions.values('pk')
            )

        if randomization_version:
            exam_questions_json = convert_json_to_choice_exam_questions_list(randomization_version.exam_json)
            exam_question_student_pks = [q['pk'] for q in exam_questions_json]
            preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(exam_question_student_pks)])
            exam_questions = exam_questions.filter(pk__in=exam_question_student_pks).order_by(preserved)

        context['object'] = self.object.application
        context['application_students'] = [self.object]
        context['exam_questions'] = exam_questions
        context['randomization_version'] = randomization_version
        context['qr_code_text'] = qr_code_text
        context['client'] = self.object.student.client
        context['disable_support_chat'] = True
        context['disable_sleek'] = True
        context['disable_strip'] = self.object.student.client.disable_stripped_answer_sheet
        context['application_randomization_version'] = []
        return context


class PrintDetachedAnswerSheetView(LoginOrTokenRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = [settings.COORDINATION, ]
    template_name = 'omr/export_answer_sheets.html'
    model = Application

    def dispatch(self, request, *args, **kwargs):
        self.is_enem = bool(request.GET.get('enem', 0))
        self.is_hybrid = bool(request.GET.get('hybrid', 0))
        self.is_sum = bool(request.GET.get('sum', 0))
        self.is_subjects = bool(request.GET.get('subjects', 0))
        self.is_reduced = bool(request.GET.get('reduced', 0))

        return super(PrintDetachedAnswerSheetView, self).dispatch(request, *args, **kwargs)

    def get_object(self):
        return self.model.objects.using('default').get(
            pk=self.kwargs['pk']
        )

    def get_template_names(self):
        if self.is_enem:
            return ['omr/export_answer_sheets_enem_new.html']
        elif self.is_hybrid:
            return ['omr/export_answer_sheets_hybrid.html']
        elif self.is_sum:
            return ['omr/mockups/answer_sheet_sum.html']
        elif self.is_subjects:
            return ['omr/mockups/answer_sheet_subjects.html']
        elif self.is_reduced:
            return ['omr/mockups/answer_sheet_reduced_model.html']
        return ['omr/export_answer_sheets.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        exam = self.object.exam

        application_students = [
            ApplicationStudent(application=self.object)
        ]
        application_students[0].detached = True

        sequential = OMRCategory.FISCALLIZE
        if self.is_enem:
            sequential = OMRCategory.ENEM
        elif self.is_hybrid:
            sequential = OMRCategory.HYBRID_025
        elif self.is_sum:
            sequential = OMRCategory.SUM_1
        elif self.is_subjects:
            sequential = OMRCategory.SUBJECTS_1
        elif self.is_reduced:
            sequential = OMRCategory.REDUCED_MODEL

        application_students[0].qr_code = get_qr_code(
            self.object.pk,
            sequential=sequential,
            operation_type='A',
        )
        qr_code_text = f'A:{sequential}:{self.object.pk}'

        exam_questions = ExamQuestion.objects.filter(
            exam=exam
        ).availables().order_by(
            'exam_teacher_subject__order', 'order'
        ).using('default')

        if self.is_subjects:
            exam_questions = exam_questions.filter(
                question__number_is_hidden=False,
                question__category=Question.CHOICE,
            ).order_by()

            if self.object.exam.is_abstract:
                exam_questions = exam_questions.annotate(
                    subject=F('question__subject__name')
                ).order_by('order')
            else:
                exam_json = get_exam_base_json(self.object.exam)
                exam_questions_list = convert_json_to_choice_exam_questions_list(exam_json)
                exam_questions_pks = [q['pk'] for q in exam_questions_list]

                exam_questions = exam_questions.get_ordered_pks(
                    exam_questions_pks
                ).annotate(
                    subject=F('exam_teacher_subject__teacher_subject__subject__name')
                )

        elif exam.has_foreign_languages:
            if exam.is_abstract:
                questions = exam.get_foreign_exam_questions()
                last_foreign_language_questions = questions[questions.count()//2:]
            elif foreign_subjects := exam.get_foreign_exam_teacher_subjects():
                last_foreign_language_questions = foreign_subjects[1].examquestion_set.using('default').availables()

            exam_questions = exam_questions.exclude(
                pk__in=last_foreign_language_questions.values('pk') 
            )

        context['application_students'] = application_students
        context['exam_questions'] = exam_questions
        context['qr_code_text'] = qr_code_text
        context['client'] = exam.coordinations.all().first().unity.client
        context['disable_support_chat'] = True
        context['disable_sleek'] = True
        context['application_randomization_version'] = []

        if self.is_reduced:
            context['detached'] = True
            context['application_students'] = None

        if exam.coordinations.exists():
            context['disable_strip'] = exam.coordinations.first().unity.client.disable_stripped_answer_sheet
        
        return context

class PrintApplicationAttendanceListView(LoginOrTokenRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = ['coordination', ]
    template_name = "distribution/lists/attendance_list.html"
    model = Application

    def dispatch(self, request, *args, **kwargs):
        activate('pt-br')
        return super().dispatch(request, *args, **kwargs)

    def get_application_students(self):
        application_students =  ApplicationStudent.objects.filter(
            application=self.object,
        )
        
        if school_class_id := self.request.GET.get('school_class', None):
            application_students = application_students.filter_by_school_class(
                school_class_id,
            ).order_by('student__name') 

        return application_students
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rooms_distributions_student'] = self.get_application_students()
        context['object'] = SchoolClass.objects.filter(pk=self.request.GET.get('school_class', None)).first()
        context['application'] = self.object
        context['hide_dialog'] = True
        context['available_languages'] = ["pt-br"]
        return context


class ExportAnswerSheetsDetachedView(LoginRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = [settings.COORDINATION, ]

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_omr:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('applications:applications_list'))

        return super(ExportAnswerSheetsDetachedView, self).dispatch(request, *args, **kwargs)

    def get_exam_safe(self, application):
        exam_name_no_spaces = re.sub(r'[\s]+|/', '_', application.exam.name)
        return re.sub(r'[^a-zA-Z0-9_]+', '', exam_name_no_spaces)

    def get_sheet_file(self, sheet_url, application, reduced=False):
        data = {
            "url": settings.BASE_URL + sheet_url,
            "filename": f'detached_{str(application.pk)}.pdf',
            "check_loaded_element": True,
        }

        print_url = settings.LOCAL_PRINTING_SERVICE_BASE_URL + settings.PRINTING_SERVICE_PATH
        with get_session_retry().post(print_url, json=data, stream=True) as r:
            sheet_file = BytesIO(r.content)
            sheet_file.seek(0)

        if reduced:
            sheet_file = Pdf.open(sheet_file)
            result_pdf = Pdf.new()

            result_pdf.add_blank_page(page_size=(842, 595))
            destination_page = Page(result_pdf.pages[0])
            destination_page.add_overlay(Page(sheet_file.pages[0]), Rectangle(-1, 0, 420, 595))
            
            buffered_file = BytesIO()
            result_pdf.save(buffered_file)
            buffered_file.seek(0)
            sheet_file = buffered_file

        return sheet_file

    def get_exam(self, application, application_student=None):
        print_url = settings.LOCAL_PRINTING_SERVICE_BASE_URL + settings.PRINTING_SERVICE_PATH

        exam_print_url = settings.BASE_URL + reverse('exams:exam_print', kwargs={'pk': application.exam_id})
        exam_print_url += f'?{application.exam.get_printing_params()}&pass_check_can_print=1'

        if application_student:
            exam_print_url += f'&application_student={application_student.pk}'

        data = {
            "url": exam_print_url,
            "filename": f'exam_{str(application.pk)}.pdf',
            "check_loaded_element": True,
            "wait_seconds": True,
        }

        with get_session_retry().post(print_url, json=data, stream=True) as r:
            exam_file = BytesIO(r.content)
            exam_file.seek(0)

        return exam_file

    def post(self, request, *args, **kwargs):
        try:
            application = Application.objects.get(pk=self.kwargs.get('pk'))
            exam = application.exam
            application_student = None

            answer_sheet_model = request.POST.get('answer_sheet_model', 'fiscallize')
            include_exam = int(request.POST.get('include_exam', False))

            if student_id := request.POST.get('student_id', None):
                student = Student.objects.get(pk=student_id)
                application_student, _ = ApplicationStudent.objects.get_or_create(
                    application=application,
                    student=student,
                )

            print(f'Imprimindo folha de respostas modelo {answer_sheet_model}. Application Student: {application_student or "vazio"}')

            if answer_sheet_model == 'discursive':
                print_urls = []

                exam_has_discursive_without_essay = exam.questions.availables(exam).filter(
                    category__in=[Question.TEXTUAL, Question.FILE],
                    is_essay=False,
                )

                if exam_has_discursive_without_essay:
                    if application_student:
                        print_urls.append(reverse('omr:print_discursive_answer_sheet', kwargs={'pk': application_student.pk}))
                    else:
                        print_urls.append(reverse('omr:print_detached_discursive_answer_sheet', kwargs={'pk': application.pk}))

                if exam.has_essay_questions:
                    if application_student:
                        print_urls.append(reverse('omr:export_application_student_essay_sheet', kwargs={'pk': application_student.pk}))
                        print_urls.append(reverse('omr:export_application_student_essay_sheet', kwargs={'pk': application_student.pk})+'?is_draft=1')
                    else:
                        print_urls.append(reverse('omr:export_detached_essay_sheet', kwargs={'pk': application.pk}))
                        print_urls.append(reverse('omr:export_detached_essay_sheet', kwargs={'pk': application.pk}) + '?is_draft=1')

                discursive_files = []
                for print_url in print_urls:
                    discursive_files.append(self.get_sheet_file(print_url, application))

                if include_exam:
                    discursive_files.append(self.get_exam(application, application_student))

                sheet_file = reduce(merge_memory_pdfs, discursive_files)
                sheet_file.seek(0)

                response = HttpResponse(sheet_file, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="Folha_de_Respostas_Avulsa_{self.get_exam_safe(application)}.pdf"'
                return response

            print_url = reverse('omr:print_detached_answer_sheet', kwargs={'pk': application.pk})
            if application_student:
                print_url = reverse('omr:print_application_student_answer_sheet', kwargs={'pk': application_student.pk})

            if answer_sheet_model == 'enem':
                print_url += f'?enem=1'
            elif answer_sheet_model == 'hybrid':
                print_url += f'?hybrid=1'
            elif answer_sheet_model == 'sum':
                print_url += f'?sum=1'
            elif answer_sheet_model == 'subjects':
                print_url += f'?subjects=1'
            elif answer_sheet_model == 'reduced':
                print_url += f'?reduced=1'

            is_reduced = answer_sheet_model == 'reduced'
            file = self.get_sheet_file(print_url, application, is_reduced)

            if include_exam:
                file = merge_memory_pdfs(file, self.get_exam(application, application_student))
                file.seek(0)

            response = HttpResponse(file, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Folha_de_Respostas_Avulsa_{self.get_exam_safe(application)}.pdf"'
            return response

        except Exception as e:
            logger = logging.getLogger('fiscallizeon')
            remote_address = self.request.META.get('HTTP_X_FORWARDED_FOR') or self.request.META.get('REMOTE_ADDR')
            logger.error(e, extra={
                'remote_address': remote_address,
                'user': self.request.user,
                'user_pk': self.request.user.pk,
            })

class ExportDiscursiveAnswerSheetsDetachedView(LoginRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = [settings.COORDINATION, ]

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_discursive_omr:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('applications:applications_list'))

        self.is_enem = bool(request.GET.get('enem', 0))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        try:
            application = Application.objects.get(pk=self.kwargs.get('pk'))
            
            # if not application.exam.can_print:
            #     remote_address = self.request.META.get('HTTP_REFERER')
            #     messages.error(request, "O caderno não pode ser impresso, por que existe um malote associado, ou o caderno foi marcado como já impresso.")
            #     return HttpResponseRedirect(remote_address)
            
            print_url = reverse(
                'omr:print_detached_discursive_answer_sheet',
                kwargs={'pk': application.pk}
            )

            data = {
                "url": settings.BASE_URL + print_url,
                "filename": f'detached_{str(application.pk)}.pdf',
            }

            auth_token = get_service_account_oauth2_token(settings.PRINTING_SERVICE_BASE_URL)
            headers = {"Authorization": f"Bearer {auth_token}"}

            print_url = settings.PRINTING_SERVICE_BASE_URL + settings.PRINTING_SERVICE_PATH
            with get_session_retry().post(print_url, json=data, headers=headers, stream=True) as r:
                file = BytesIO(r.content)
                file.seek(0)

            exam_name_no_spaces = re.sub(r'[\s]+|/', '_', application.exam.name)
            exam_name_safe = re.sub(r'[^a-zA-Z0-9_]+', '', exam_name_no_spaces)

            response = HttpResponse(file, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Folha_de_Respostas_Discursiva_Avulsa_{exam_name_safe}.pdf"'
            return response

        except Exception as e:
            logger = logging.getLogger('fiscallizeon')
            remote_address = self.request.META.get('HTTP_X_FORWARDED_FOR') or self.request.META.get('REMOTE_ADDR')
            logger.error(e, extra={
                'remote_address': remote_address,
                'user': self.request.user,
                'user_pk': self.request.user.pk,
            })


class AnswerSheetsListView(LoginRequiredMixin, CheckHasPermission, ListView):
    model = OMRUpload
    # template_name = 'omr/omr_upload_list.html'
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    permission_required = 'omr.view_omrupload'
    paginate_by = 15

    def get_template_names(self):
        if self.request.GET.get('v') or self.request.user.client_enabled_new_answer_sheet_experience:
            return 'omr/omr_upload_list_new.html'
        return 'omr/omr_upload_list.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_omr:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('applications:applications_list'))

        return super(AnswerSheetsListView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super(AnswerSheetsListView, self).get_queryset()
        queryset = queryset.filter(
            school_class__isnull=True
        ).exclude(
            deleted_at__isnull=False
        )

        if self.request.user.user_type == settings.TEACHER:
            queryset = queryset.filter(user=self.request.user).order_by('-created_at')

        elif self.request.user.can_see_all():
            queryset = queryset.filter(
                user__coordination_member__coordination__unity__client__in=self.request.user.get_clients_cache()
            ).distinct().select_related('user').order_by('-created_at')
        else:
            queryset = queryset.filter(
                user__coordination_member__coordination__in=self.request.user.get_coordinations_cache()
            ).distinct().select_related('user').order_by('-created_at')

        today = timezone.localtime(timezone.now())
        
        if self.request.GET.get('year'):
            queryset = queryset.filter(
                created_at__date__year=self.request.GET.get('year'),
            )
        else:
            queryset = queryset.filter(
                created_at__date__year=today.year,
            )
        
        # Filters templates
        if self.request.GET.get('q_exam'):
            
            query_terms = [Q(application_students__application__exam__name__icontains=term) for term in self.request.GET.get('q_exam').split(' ')]
            query = Q()
            
            for quey in query_terms:
                query &= quey

            queryset = queryset.prefetch_related(
                'application_students__application__exam'
            ).filter(
                query
            )

        if self.request.GET.get('q_initial_date') and not self.request.GET.get('q_final_date'):
            queryset = queryset.filter(
                created_at__date=self.request.GET.get('q_initial_date')
            ).order_by('created_at')
        
        if self.request.GET.get('q_final_date') and not self.request.GET.get('q_initial_date'):
            queryset = queryset.filter(
                created_at__lte=self.request.GET.get('q_final_date')
            ).order_by('created_at')

        if self.request.GET.get('q_initial_date') and self.request.GET.get('q_final_date'):
            queryset = queryset.filter(created_at__date__range=(self.request.GET.get('q_initial_date'), self.request.GET.get('q_final_date'))).order_by('created_at')

        if self.request.GET.getlist('q_classes'):
            queryset = queryset.filter(
                application_students__student__classes__in=self.request.GET.getlist('q_classes', ''),
                application_students__student__classes__school_year=timezone.now().year if not self.request.GET.get('year') else self.request.GET.get('year')
            )

        if self.request.GET.getlist('q_grades'):
            queryset = queryset.filter(
                application_students__student__classes__grade__in=self.request.GET.getlist('q_grades', ""),
                application_students__student__classes__school_year=timezone.now().year if not self.request.GET.get('year') else self.request.GET.get('year')
            )

        if self.request.GET.getlist('q_unitys'):
            unity_id = self.request.GET.getlist('q_unitys', [])

            users = list(CoordinationMember.objects.prefetch_related('coordination__unity').filter(
                coordination__unity__in=unity_id
            ).values_list('user_id'))

            # students = list(Student.objects.prefetch_related('classes__coordination__unity').filter(
            #     classes__coordination__unity__in=unity_id, classes__school_year=timezone.now().year
            # ).annotate(pk_str=Cast(F('pk'), CharField())).values_list('pk_str', flat=True))

            queryset = queryset.prefetch_related('user').filter(
                Q(
                    # Q(application_students__student=students) &
                    Q(user__in=users)
                )
            )
        
        if self.request.GET.get('q_filename'):
            queryset = queryset.filter(
                filename__icontains=self.request.GET.get('q_filename', "")
            )


        if self.request.GET.get('q_errors'):
            queryset = queryset.filter(
                omrerror__is_solved=False
            )

        if self.request.GET.get('q_repeated_file'):
            queryset = queryset.annotate(
                has_duplicates=Exists(
                    OMRUpload.objects.filter(
                        filename=OuterRef('filename'),
                        created_at__date__year=today.year,
                        user__coordination_member__coordination__unity__client__in=self.request.user.get_clients_cache()
                    ).exclude(pk=OuterRef('pk'))
                )
            ).filter(
                has_duplicates=True
            )
        
        if self.request.GET.get('q_categorys'):
            queryset = queryset.filter(
                omrerror__category__in=self.request.GET.getlist('q_categorys', "")
            )

        q_status = self.request.GET.get('q_status', "all")

        if q_status and not q_status == "all":
            queryset = queryset.filter(
                status=q_status
            )
        
        return queryset.only(
            'pk', 'created_at', 'user__name', 'filename', 'status', 'total_pages',
        )

    def get_context_data(self, **kwargs):
        
        today = timezone.localtime(timezone.now())
        
        context = super(AnswerSheetsListView, self).get_context_data(**kwargs)
        form = AnswerSheetForm()
        form.fields['omr_category'].queryset = OMRCategory.objects.filter(
                clients__in=self.request.user.get_clients(),
                is_native=False,
            ).distinct()
        context['form'] = form

        context['year'] = str(today.year).replace(".", "")
        if self.request.GET.get('year'):
            context['year'] = self.request.GET.get('year')

        context['q_exam'] = self.request.GET.get('q_exam', '')
        context['q_initial_date'] = self.request.GET.get('q_initial_date', '')
        context['q_final_date'] = self.request.GET.get('q_final_date', '')
        context['q_classes'] = self.request.GET.getlist('q_classes', '')
        context['q_grades'] = self.request.GET.getlist('q_grades', '')
        context['q_unitys'] = self.request.GET.getlist('q_unitys', '')
        context['q_errors'] = self.request.GET.get('q_errors', '')
        context['q_repeated_file'] = self.request.GET.get('q_repeated_file', '')
        context['q_categorys'] = self.request.GET.getlist('q_categorys', '')
        context['q_errors_solved'] = self.request.GET.get('q_errors_solved', '')
        context['q_status'] = self.request.GET.get('q_status', 'all')
        context['q_filename'] = self.request.GET.get('q_filename', '')

        
        list_filters = [
            context['q_exam'], context['q_initial_date'], context['q_final_date'], 
            context['q_classes'], context["q_grades"], context["q_unitys"], 
            context["q_errors"], context['q_categorys'], context['q_status'] if context['q_status'] != 'all' else '',
            context['q_filename'], context["q_repeated_file"]
        ]

        context['count_filters'] = len(list_filters) - list_filters.count('')

        context['classes'] = self.request.user.get_coordinations_school_classes(
            year=context['year'],
        )

        context["grades"] = Grade.objects.all()
        context['unitys'] = Unity.objects.filter(
            client=self.request.user.client
        ).distinct().select_related('client')
        
        return context

class ImportAnswerSheetsView(LoginRequiredMixin, CheckHasPermission, FormView):
    template_name = 'omr/omr_upload_list.html'
    form_class = AnswerSheetForm
    required_permissions = [settings.COORDINATION, settings.TEACHER]

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_omr:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('applications:applications_list'))

        return super(ImportAnswerSheetsView, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return redirect(reverse('omr:omr_upload_list'))

    def get_success_url(self, **kwargs):
        return reverse('omr:omr_upload_list')

    def form_invalid(self, form):
        print(form.errors)
        return super().form_invalid(form)

    def form_valid(self, form):
        application = None
        if application_id := form.cleaned_data.get('application', None):
            application = Application.objects.get(pk=application_id)

        omr_upload = OMRUpload.objects.create(
            user=self.request.user,
            filename=form.cleaned_data.get('pdf_scan'),
            raw_pdf=form.cleaned_data.get('pdf_scan'),
            omr_category=form.cleaned_data.get('omr_category', None),
            ignore_qr_codes=form.cleaned_data.get('ignore_qr_codes', False),
            gamma_option=form.cleaned_data.get('gamma_option', 1),
            application=application,
        )
        
        if category := omr_upload.omr_category:
            if category.sequential in [3, 4, 5 ,6]:
                proccess_sheets_rio.apply_async(args=[omr_upload.pk])
                return super().form_valid(form)
            elif category.sequential == 7:
                proccess_sheets_eleva.apply_async(args=[omr_upload.pk])
                return super().form_valid(form)
            elif category.sequential == 9:
                proccess_sheets_salta.apply_async(args=[omr_upload.pk])
                return super().form_valid(form)
            elif category.sequential == 10:
                process_elit_sheets.apply_async(args=[omr_upload.pk])
                return super().form_valid(form)
            elif category.sequential == OMRCategory.SESI_32:
                proccess_sheets_sesi.apply_async(args=[omr_upload.pk])
                return super().form_valid(form)
        
        proccess_sheets.apply_async(
            args=[omr_upload.pk],
        )

        return super().form_valid(form)
    

class ImportOffsetSchoolClassAnswerSheetsView(LoginRequiredMixin, CheckHasPermission, FormView):
    template_name = 'omr/omr_upload_offset_schoolclass_list.html'
    form_class = OffsetSchoolClassAnswerSheetForm
    required_permissions = [settings.COORDINATION, ]

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_omr:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('applications:applications_list'))

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return redirect(reverse('omr:omr_upload_offset_schoolclass_list'))

    def get_success_url(self, **kwargs):
        return reverse('omr:omr_upload_offset_schoolclass_list')

    def form_invalid(self, form):
        print(form.errors)
        return super().form_invalid(form)

    def form_valid(self, form):
        application = Application.objects.get(
            pk=form.cleaned_data.get('application')
        )
        school_class = SchoolClass.objects.get(
            pk=form.cleaned_data.get('school_class')
        )

        omr_upload = OMRUpload.objects.create(
            user=self.request.user,
            application=application,
            school_class=school_class,
            filename=form.cleaned_data.get('pdf_scan'),
            raw_pdf=form.cleaned_data.get('pdf_scan'),
            gamma_option=form.cleaned_data.get('gamma_option', 1),
        )
        
        proccess_sheets_offset.apply_async(
            args=[omr_upload.pk],
        )

        return super().form_valid(form)


class OffsetSchoolUploadListView(LoginRequiredMixin, CheckHasPermission, ListView):
    model = OMRUpload
    form_class = OffsetSchoolClassAnswerSheetForm
    template_name = 'omr/omr_upload_offset_schoolclass_list.html'
    required_permissions = [settings.COORDINATION, ]
    permission_required = 'omr.view_omrupload'
    paginate_by = 15

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_omr:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('applications:applications_list'))

        return super(OffsetSchoolUploadListView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super(OffsetSchoolUploadListView, self).get_queryset()
        queryset = queryset.filter(school_class__isnull=False)

        if self.request.user.can_see_all():
            queryset = queryset.filter(
                user__coordination_member__coordination__unity__client__in=self.request.user.get_clients_cache()
            ).distinct().select_related('user').order_by('-created_at')
        else:
            queryset = queryset.filter(
                user__coordination_member__coordination__in=self.request.user.get_coordinations_cache()
            ).distinct().select_related('user').order_by('-created_at')

        today = timezone.localtime(timezone.now())
        
        if self.request.GET.get('year'):
            queryset = queryset.filter(
                created_at__date__year=self.request.GET.get('year'),
            )
        else:
            queryset = queryset.filter(
                created_at__date__year=today.year,
            )
        
        # Filters templates
        if q_exam := self.request.GET.get('q_exam'):

            application_students_qs = ApplicationStudent.objects.filter(
                omr_uploads=OuterRef('pk'),
                application__exam__name__icontains=q_exam
            )

            queryset = queryset.filter(
                Exists(application_students_qs)
            )

        if self.request.GET.get('q_initial_date') and not self.request.GET.get('q_final_date'):
            queryset = queryset.filter(
                created_at__date=self.request.GET.get('q_initial_date')
            ).order_by('created_at')
        
        if self.request.GET.get('q_final_date') and not self.request.GET.get('q_initial_date'):
            queryset = queryset.filter(
                created_at__lte=self.request.GET.get('q_final_date')
            ).order_by('created_at')

        if self.request.GET.get('q_initial_date') and self.request.GET.get('q_final_date'):
            queryset = queryset.filter(created_at__date__range=(self.request.GET.get('q_initial_date'), self.request.GET.get('q_final_date'))).order_by('created_at')

        if self.request.GET.getlist('q_classes'):
            queryset = queryset.filter(
                application_students__student__classes__in=self.request.GET.getlist('q_classes', ''),
                application_students__student__classes__school_year=timezone.now().year if not self.request.GET.get('year') else self.request.GET.get('year')
            )

        if self.request.GET.getlist('q_grades'):
            queryset = queryset.filter(
                application_students__student__classes__grade__in=self.request.GET.getlist('q_grades', ""),
                application_students__student__classes__school_year=timezone.now().year if not self.request.GET.get('year') else self.request.GET.get('year')
            )

        if self.request.GET.getlist('q_unities'):
            unities_ids = self.request.GET.getlist('q_unities', [])

            users = list(CoordinationMember.objects.prefetch_related('coordination__unity').filter(
                coordination__unity__in=unities_ids
            ).values_list('user_id'))

            queryset = queryset.prefetch_related('user').filter(
                Q(
                    # Q(application_students__student=students) &
                    Q(user__in=users)
                )
            )
        
        if self.request.GET.get('q_filename'):
            queryset = queryset.filter(
                filename__icontains=self.request.GET.get('q_filename', "")
            )

        if self.request.GET.get('q_errors'):
            queryset = queryset.filter(
                omrerror__is_solved=False
            )

        q_status = self.request.GET.get('q_status', "all")

        if q_status and not q_status == "all":
            queryset = queryset.filter(
                status=q_status
            )
        
        return queryset.only(
            'pk', 'created_at', 'user__name', 'filename', 'status', 'total_pages',
        )

    def get_context_data(self, **kwargs):
        today = timezone.localtime(timezone.now())
        
        context = super().get_context_data(**kwargs)
        context['form'] = OffsetSchoolClassAnswerSheetForm()
        context['year'] = str(today.year).replace(".", "")
        if self.request.GET.get('year'):
            context['year'] = self.request.GET.get('year')

        context['q_exam'] = self.request.GET.get('q_exam', '')
        context['q_initial_date'] = self.request.GET.get('q_initial_date', '')
        context['q_final_date'] = self.request.GET.get('q_final_date', '')
        context['q_classes'] = self.request.GET.getlist('q_classes', '')
        context['q_grades'] = self.request.GET.getlist('q_grades', '')
        context['q_unities'] = self.request.GET.getlist('q_unities', '')
        context['q_errors'] = self.request.GET.get('q_errors', '')
        context['q_status'] = self.request.GET.get('q_status', 'all')
        context['q_filename'] = self.request.GET.get('q_filename', '')

        list_filters = [
            context['q_exam'], context['q_initial_date'], context['q_final_date'], 
            context['q_classes'], context["q_grades"], context["q_unities"], 
            context['q_status'] if context['q_status'] != 'all' else '',
            context['q_filename']
        ]

        context['count_filters'] = len(list_filters) - list_filters.count('')

        context['classes'] = self.request.user.get_coordinations_school_classes(
            year=context['year']
        )

        context["grades"] = Grade.objects.all()
        context['unities'] = Unity.objects.filter(
            client__in=self.request.user.get_clients_cache()
        ).distinct().select_related('client')
        
        return context


class ImportAnswerSheetsApiView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        serializer = AnswerSheetSerializer(data=request.data)

        if serializer.is_valid():
            omr_upload = OMRUpload.objects.create(
                user=request.user,
                filename=serializer.validated_data['pdf_scan'],
                raw_pdf=serializer.validated_data['pdf_scan'],
                omr_category=serializer.validated_data.get('omr_category', None),
            )

            if category := omr_upload.omr_category:
                if category.sequential in [3, 4, 5 ,6]:
                    proccess_sheets_rio.apply_async(args=[omr_upload.pk])
                elif category.sequential == 7:
                    proccess_sheets_eleva.apply_async(args=[omr_upload.pk])
                elif category.sequential == 9:
                    proccess_sheets_salta.apply_async(args=[omr_upload.pk])
                elif category.sequential == 10:
                    process_elit_sheets.apply_async(args=[omr_upload.pk])

            proccess_sheets.apply_async(args=[omr_upload.pk])

            str_omr_upload_created_at = formats.date_format(
                timezone.localtime(omr_upload.created_at),
                format='d/m/Y \à\s G\:i'
            )
            return Response(
                {
                    'id': omr_upload.id,
                    'createdDate': str_omr_upload_created_at,
                    'user': f'{omr_upload.user}',
                    'filename': f'{omr_upload.filename}',
                    'status': omr_upload.status,
                    'statusDescription': omr_upload.get_status_display(),
                    'errorsCounter': omr_upload.total_errors_count,
                    'totalPages': omr_upload.total_pages,
                    'classes': [{'name': class_} for class_ in omr_upload.get_classes],
                    'studentPageErrorCountLoading': True,
                    'studentPageErrorCount': None,
                    'fullUrl': omr_upload.get_full_url(),
                },
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RetryImportAnswerSheetsView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        omr_upload = OMRUpload.objects.using('default').get(pk=self.kwargs['pk'])
        if omr_upload.can_be_reprocessed:
            upload_dir = os.path.join(settings.OMR_UPLOAD_DIR, str(omr_upload.pk))

            if os.path.isdir(upload_dir): 
                shutil.rmtree(upload_dir, ignore_errors=True)

            # omr_upload.ignore_qr_codes = bool(self.request.GET.get('ignore_qr_codes', False))
            omr_upload.gamma_option = self.request.GET.get('gamma_option', 1)
            omr_upload.status = OMRUpload.PENDING
            omr_upload.save()

            OMRError.objects.filter(upload=omr_upload).delete()

            AsyncResult(f'PROCESS_LIZE_SHEETS_{omr_upload.pk}').forget()
            proccess_sheets.apply_async(args=[omr_upload.pk])
        return reverse('omr:omr_upload_list')


class OMRUploadDetailView(LoginRequiredMixin, CheckHasPermission, DetailView):
    # template_name = 'omr/omr_upload_detail.html'
    permission_required = 'omr.view_omrupload'
    model = OMRUpload
    required_permissions = [settings.COORDINATION, settings.TEACHER]

    def get_queryset(self):
        return super().get_queryset().exclude(deleted_at__isnull=False)

    def get_template_names(self):
        if self.request.GET.get('v'):
            return 'omr/omr_upload_detail_new.html'
        return 'omr/omr_upload_detail.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_omr:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('applications:applications_list'))

        return super(OMRUploadDetailView, self).dispatch(request, *args, **kwargs)

    def get_error_list(self):
        errors = []
        for error in self.object.get_unsolved_errors():
            errors.append({
                'omr_error': str(error.pk),
                'error_image': error.error_image.url if error.error_image else "",
                'page_number': error.page_number,
                'randomization_version': error.randomization_version,
                'category_description': error.get_category_display(),
                'omr_category': error.omr_category.pk if error.omr_category else '',
                'student': error.student,
                'application': error.application,
            })

        return errors

    def get_discursive_errors_list(self):
        errors = []
        for error in self.object.get_unsolved_discursive_errors():
            errors.append({
                'omr_error': str(error.pk),
                'error_image': error.error_image.url if error.error_image else "",
                'category_description': error.get_category_display(),
                'application_student_instance': error.application_student,
                'application_student': error.application_student.pk,
                'version_number': error.version_number,
                'omr_category': error.omr_category,
                'exam_question': '',
            })

        return errors

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        errors_list = self.get_error_list()
        formset = OMRErrorFormSet(initial=errors_list)
        for i, form in enumerate(formset.forms):
            form.fields['student'].initial = errors_list[i]['student']
            form.fields['omr_category'].queryset = OMRCategory.objects.filter(
                clients__in=self.request.user.get_clients()
            ).distinct()

        discursive_errors_list = self.get_discursive_errors_list()
        formset_discursive = OMRDiscursiveErrorFormSet(initial=discursive_errors_list)

        for i, form in enumerate(formset_discursive.forms):
            application_student = discursive_errors_list[i]['application_student_instance']
            exam_questions = ExamQuestion.objects.filter(
                    exam=application_student.application.exam,
                    question__category__in=[Question.FILE, Question.TEXTUAL]
            ).availables()

            form.fields['exam_question'].queryset = exam_questions            

            if version_number := discursive_errors_list[i]['version_number']:
                exam = application_student.application.exam
                randomization_version = RandomizationVersion.objects.filter(
                    application_student=application_student,
                    version_number=version_number,
                ).first()

                for exam_question in form.fields['exam_question'].queryset:
                    exam_question.randomized_print_number = exam.number_print_question(
                        question=exam_question.question, 
                        randomization_version=randomization_version,
                    )

            form.fields['omr_category'].queryset = OMRCategory.objects.filter(
                    clients__in=self.request.user.get_clients(),
                    is_discursive=True,
                ).distinct()

        context['formset'] = formset
        context['formset_discursive'] = formset_discursive
        context['reprocess_form'] = AnswerSheetForm()
        context['omr_students'] = OMRStudents.objects.filter(
            upload=self.object
        ).annotate_discursive_scans()
        
        return context

class OMRuploadFixView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        formset = OMRErrorFormSet(self.request.POST, self.request.FILES)

        if formset.is_valid():
            cleaned_data = formset.cleaned_data
            valid_corrections = []
            valid_corrections_salta = []
            valid_corrections_elit = []
            valid_corrections_sesi = []
            
            for form_data in cleaned_data:
                del form_data['error_image']
                student = form_data.get('student', None)
                form_data['student'] = student.pk if student else None

                if student and form_data.get('application', None) and form_data.get('omr_category', None):
                    if form_data.get('omr_category', 1) == OMRCategory.SALTA_DEFAULT:
                        valid_corrections_salta.append(form_data)
                        continue
                    if form_data.get('omr_category', 1) == OMRCategory.ELIT:
                        valid_corrections_elit.append(form_data)
                        continue
                    if form_data.get('omr_category', 1) == OMRCategory.SESI_32:
                        valid_corrections_sesi.append(form_data)
                        continue

                    valid_corrections.append(form_data)

            if not valid_corrections and not valid_corrections_salta and not valid_corrections_elit and not valid_corrections_sesi:
                messages.warning(self.request, 'Você deve selecionar pelo menos um erro de leitura para corrigir, preenchendo o tipo de gabarito, o aluno e a aplicação')
                return reverse('omr:omr_upload_detail', kwargs={'pk': kwargs['pk']})

            if valid_corrections:
                reproccess_sheets.apply_async(
                    args=[self.kwargs['pk'], valid_corrections],
                )

            if valid_corrections_salta:
                reproccess_sheets_salta.apply_async(
                    args=[self.kwargs['pk'], valid_corrections_salta],
                )

            if valid_corrections_elit:
                reproccess_sheets_elit.apply_async(
                    args=[self.kwargs['pk'], valid_corrections_elit],
                )

            if valid_corrections_sesi:
                reproccess_sheets_sesi.apply_async(
                    args=[self.kwargs['pk'], valid_corrections_sesi],
                )

            omr_upload = OMRUpload.objects.get(pk=kwargs['pk'])
            omr_upload.status = OMRUpload.REPROCESSING
            omr_upload.save()
            return reverse('omr:omr_upload_detail', kwargs={'pk': kwargs['pk']})
        else:
            print(formset.errors)
            capture_message(f'LOG - {formset.errors}')
            return reverse('omr:omr_upload_detail', kwargs={'pk': kwargs['pk']})
        

class OMRDiscursiveUploadFixView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        formset = OMRDiscursiveErrorFormSet(self.request.POST, self.request.FILES)

        if formset.is_valid():
            cleaned_data = formset.cleaned_data
            valid_corrections = []

            for form_data in cleaned_data:
                omr_discursive_error = OMRDiscursiveError.objects.get(pk=form_data.get('omr_error'))
                if not omr_discursive_error or not form_data['exam_question'] or not form_data['omr_category']:
                    continue

                valid_corrections.append({
                    "page_number": 0,
                    "ignore_omr_scan": True,
                    "operation_type": "S",
                    "sequential": form_data.get('omr_category').sequential,
                    "randomization_version": None,
                    "file_path": "",
                    "object_id": str(form_data.get('application_student')),
                    "answers_data": [
                        {
                            "omr_error": str(form_data.get('omr_error')),
                            "application_student_pk": str(form_data.get('application_student')),
                            "exam_question_pk": str(form_data.get('exam_question').pk),
                            "image_path": str(omr_discursive_error.error_image),
                        }
                    ]
                })

            if valid_corrections:
                reproccess_discursive_questions.apply_async(
                    args=[self.kwargs['pk'], valid_corrections]
                )
                omr_upload = OMRUpload.objects.get(pk=kwargs['pk'])
                omr_upload.status = OMRUpload.REPROCESSING
                omr_upload.save()

            return reverse('omr:omr_upload_detail', kwargs={'pk': kwargs['pk']})
        else:
            print(formset.errors)
            capture_message(f'LOG - {formset.errors}')
            return reverse('omr:omr_upload_detail', kwargs={'pk': kwargs['pk']})


class TemplateListView(LoginRequiredMixin, CheckHasPermission, ListView):
    model = Exam
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    permission_required = 'exams.view_template_exam'
    paginate_by = 30
    nps_app_label = "ExamTemplate"

    def get_template_names(self):
        if self.request.GET.get('v'):
            return 'template/template_list.html'
        return 'template/template_list_new.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_template:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super(TemplateListView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        user = self.request.user
        today = timezone.localtime(timezone.now())

        queryset_full = super(TemplateListView, self).get_queryset()

        queryset = queryset_full.using('default').filter(
            coordinations__in=user.get_coordinations_cache(),
            is_abstract=True
        ).distinct()
        
        if user.user_type == settings.TEACHER:
            queryset = queryset_full.filter(
                Q(
                    Q(coordinations__unity__client=user.client), 
                    Q(examteachersubject__teacher_subject__teacher__user=user)
                ) |
                Q(
                    Q(correction_by_subject=True),
                    Q(coordinations__unity__client=user.client), 
                    Q(examteachersubject__teacher_subject__subject__in=user.inspector.subjects.all())
                )
            )
        
        queryset = queryset.annotate(
            application_count=Count('application')
        )
    
        if self.request.GET.get('q_name', ""):
            queryset = queryset.filter(
                name__icontains=self.request.GET.get('q_name', "")
            )
            
        if self.request.GET.getlist('q_status', ""):
            queryset = queryset.filter(
                status__in=self.request.GET.get('q_status', "")
            )

        if self.request.GET.get('q_has_questions', ""):
            queryset = queryset.annotate(
                count_questions=Count('questions')
            ).filter(
                count_questions__gt=0
            )

        if self.request.GET.get('q_is_unprecedented', ""):
            queryset = queryset.filter(
                application__isnull=True
            )

        if self.request.GET.getlist('q_subjects', ""):
            filtered_exams = []
            for exam in queryset:
                if exam.get_questions().filter(subject__pk__in=self.request.GET.getlist('q_subjects', "")): filtered_exams.append(exam.pk)
            queryset = queryset.filter(
                pk__in=filtered_exams
            )

        if self.request.GET.getlist('q_grades', ""):
            filtered_exams = []
            for exam in queryset:
                if exam.get_questions().filter(grade__pk__in=self.request.GET.getlist('q_grades', "")): filtered_exams.append(exam.pk)
            queryset = queryset.filter(
                pk__in=filtered_exams
            )

        if self.request.GET.get('year'):
            queryset = queryset.filter(
                created_at__year=self.request.GET.get('year'),
            )
        else:
            queryset = queryset.filter(
                created_at__year=today.year,
            )

        # from fiscallizeon.subjects.models import Topic
        # from fiscallizeon.bncc.models import Abiliity, Competence

        # topics = Topic.objects.filter(pk__in=self.examquestion_set.availables().values_list('question__topics')).distinct()
        # abilities = Abiliity.objects.filter(pk__in=self.examquestion_set.availables().values_list('question__abilities')).distinct()
        # competences = Competence.objects.filter(pk__in=self.examquestion_set.availables().values_list('question__competences')).distinct()

        queryset = queryset.annotate(
            # topic_count=Count('examquestion__question__topics', distinct=True),
            # ability_count=Count('examquestion__question__abilities', distinct=True),
            # competence_count=Count('examquestion__question__competences', distinct=True),

            # has_topic=Exists(
            #     ExamQuestion.objects
            #     .filter(exam_id=OuterRef('id'))
            #     .availables()
            #     .order_by()
            #     .values('exam')
            #     .annotate(count=Count('question__topics'))
            #     .filter(count__gt=0)
            # ),
            # has_ability=Exists(
            #     ExamQuestion.objects
            #     .filter(exam_id=OuterRef('id'))
            #     .availables()
            #     .order_by()
            #     .values('exam')
            #     .annotate(count=Count('question__abilities'))
            #     .filter(count__gt=0)
            # ),
            # has_competence=Exists(
            #     ExamQuestion.objects
            #     .filter(exam_id=OuterRef('id'))
            #     .availables()
            #     .order_by()
            #     .values('exam')
            #     .annotate(count=Count('question__competences'))
            #     .filter(count__gt=0)
            # ),
        )
        # .annotate(
        #     quality_values=Sum(
        #         Case(
        #             When(topic_count=True, then=1),
        #             When(ability_count=True, then=1),
        #             When(competence_count=True, then=1),
        #             default=0,
        #             output_field=IntegerField()
        #         )
        #     )
        # )

        # availables_subquery = ExamQuestion.objects.filter(exam_id=OuterRef('id')).availables()
        # topic_subquery = Subquery(
        #     (
        #         availables_subquery
        #         .order_by()
        #         .values('exam')
        #         .annotate(count=Count('question__topics__id'))
        #         .values('count')
        #     ),
        #     output_field=IntegerField()
        # )
        # ability_subquery = Subquery(
        #     (
        #         availables_subquery
        #         .order_by()
        #         .values('exam')
        #         .annotate(count=Count('question__abilities__id'))
        #         .values('count')
        #     ),
        #     output_field=IntegerField()
        # )
        # competence_subquery = Subquery(
        #     (
        #         availables_subquery
        #         .order_by()
        #         .values('exam')
        #         .annotate(count=Count('question__competences__id'))
        #         .values('count')
        #     ),
        #     output_field=IntegerField()
        # )
        # queryset = queryset.annotate(
        #     topic_count=Coalesce(topic_subquery, 0),
        #     ability_count=Coalesce(ability_subquery, 0),
        #     competence_count=Coalesce(competence_subquery, 0),
        # )

        # for q in queryset:
            # print(f'sum: {q.quality_values}')
            # print(f'has topic: {q.topic_count}')
            # print(f'has ability: {q.ability_count}')
            # print(f'has competence: {q.competence_count}')
        #     print(f'topics: {q.topic_count}')
        #     print(f'abilities: {q.ability_count}')
        #     print(f'competences: {q.competence_count}')
        #     print('-----')

        return queryset.distinct().order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        today = timezone.localtime(timezone.now())
        user = self.request.user

        context = super(TemplateListView, self).get_context_data(**kwargs)
        context['q_name'] = self.request.GET.get('q_name', "")
        context['q_status'] = self.request.GET.getlist('q_status', "")
        context['q_subjects'] = self.request.GET.getlist('q_subjects', "")
        context['q_has_questions'] = self.request.GET.get('q_has_questions', "")
        context['q_is_unprecedented'] = self.request.GET.get('q_is_unprecedented', "")
        context['q_grades'] = self.request.GET.getlist('q_grades', "")

        context['exam_headers'] = ExamHeader.objects.filter(user__coordination_member__coordination__unity__client__in=self.request.user.get_clients_cache()).distinct()
        
        list_filters = [context['q_name'], context['q_status'], context['q_has_questions'], context['q_is_unprecedented'], context['q_subjects'], context["q_grades"]]

        context['count_filters'] = len(list_filters) - list_filters.count("")

        context['subjects'] = user.get_availables_subjects().select_related('knowledge_area')

        context['year'] = today.year
        if self.request.GET.get('year'):
            context['year'] = self.request.GET.get('year')
        
        context["grades"] = Grade.objects.all()

        

        return context


class TemplateUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    model = Exam
    required_permissions = [settings.COORDINATION, ]
    permission_required = 'exams.change_template_exam'
    form_class = ExamForm
    success_message = "Gabarito atualizado com sucesso!"
    nps_app_label = "ExamTemplate"

    def get_template_names(self):
        #verifica data de implantação em produção, para evitar que gabaritos antigos sejam abertos na nova interface é tenha algum tipo de incompatibilidade
        if self.request.GET.get('v') or self.get_object().created_at.date() <= datetime.datetime(2024, 1, 21).date():
            return 'template/template_update.html'
        return 'template/template_create_update_new.html'

    def get_context_data(self, **kwargs):
        context = super(TemplateUpdateView, self).get_context_data(**kwargs)
        # context["subjects"] = Subject.objects.filter(client__in=self.request.user.get_clients_cache())
        context["subjects"] = Subject.objects.all().distinct('name')
        context["grades"] = Grade.objects.all()
        context["knowledge_areas"] = KnowledgeArea.objects.all()
        context["parent_subjects"] = Subject.objects.filter(
            Q(
                Q(parent_subject__isnull=True) &
                Q(client__isnull=True)
            ) |
            Q(
                Q(parent_subject__isnull=False) &
                Q(client__in=self.request.user.get_clients_cache())
            ) | 
            Q(client__isnull=True)
        ).distinct()
        context["can_change_question_type"] = not Application.objects.filter(
                Q(
                    Q(exam=self.get_object()),
                    Q(
                        Q(answer_sheet__isnull=False),
                        ~Q(answer_sheet="")
                    )
                )
            ).exists()
        
        context["client_tags"] = QuestionTag.objects.filter(
            Q(
                Q(type=0),
                Q(
                    Q(client__in=self.request.user.get_clients_cache()) | 
                    Q(client=None)
                )
            ),
        ).order_by("name")

        exam_questions = ExamQuestion.objects.filter(exam=self.object)
        exam_questions_with_answer = [eq for eq in exam_questions if eq.has_answer]

        context['exam_questions_with_answer'] = True if exam_questions_with_answer else False

        # context['can_anull_exam_questions'] = not Application.objects.filter(
        #     Q(
        #         Q(exam=self.get_object()),
        #         Q(
        #             Q(
        #                 Q(answer_sheet__isnull=False),
        #                 ~Q(answer_sheet="")
        #             ) |
        #             Q(
        #                 Q(room_distribution__exams_bag__isnull=False),
        #                 ~Q(room_distribution__exams_bag="")
        #             )
        #         )
        #     )
        # ).exists()

        context["relations"] = SubjectRelation.objects.filter(
            client__in = self.request.user.get_clients_cache()
        )

        context["teaching_stage"] = TeachingStage.objects.filter(
            client__in = self.request.user.get_clients_cache()
        )
        
        return context

    def get_form_kwargs(self):
        kwargs = super(TemplateUpdateView, self).get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs

    def get_success_url(self):
        return reverse('omr:template_list')

class TemplateCreateTemplateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'template/template_create.html'
    required_permissions = [settings.COORDINATION, ]
    permission_required = 'exams.add_template_exam'
    nps_app_label = "ExamTemplate"

    def get_template_names(self):
        if self.request.GET.get('v'):
            return 'template/template_create.html'
        return 'template/template_create_update_new.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_template:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super(TemplateCreateTemplateView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(TemplateCreateTemplateView, self).get_context_data(**kwargs)
        # context["subjects"] = Subject.objects.filter(client__in=self.request.user.get_clients_cache())
        context["subjects"] = Subject.objects.all().distinct('name')
        context["parent_subjects"] = Subject.objects.filter(
            Q(
                Q(parent_subject__isnull=True) &
                Q(client__isnull=True)
            ) |
            Q(
                Q(parent_subject__isnull=False) &
                Q(client__in=self.request.user.get_clients_cache())
            ) | 
            Q(client__isnull=True)
        ).distinct()
        context["grades"] = Grade.objects.all()
        context["knowledge_areas"] = KnowledgeArea.objects.all()

        context["client_tags"] = QuestionTag.objects.filter(
            Q(
                Q(type=0),
                Q(
                    Q(client__in=self.request.user.get_clients_cache()) | 
                    Q(client=None)
                )
            ),
        ).order_by("name")
        
        context["relations"] = SubjectRelation.objects.filter(
            client__in = self.request.user.get_clients_cache()
        )

        context["teaching_stage"] = TeachingStage.objects.filter(
            client__in = self.request.user.get_clients_cache()
        )
        
        return context


class TemplateDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = Exam
    required_permissions = [settings.COORDINATION]
    permission_required = 'exams.delete_template_exam'
    success_message = "Prova removida com sucesso!"
    nps_app_label = "ExamTemplate"

    def get_queryset(self):
        queryset = super(TemplateDeleteView, self).get_queryset()
        return queryset.using('default')

    def form_valid(self, form):
        try:
            self.object.delete()
            get_and_create_notifications(view=self, trigger=Notification.AFTER_DELETE)
            messages.success(self.request, self.success_message)
            
        except ProtectedError:
            messages.error(self.request, "Ocorreu um erro ao remover, a prova já foi aplicada no mínimo uma vez.")
            
        return HttpResponseRedirect(self.get_success_url())
        

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER', None)


class PrintDiscursiveAnswerSheetView(LoginOrTokenRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'omr/export_discursive_answer_sheet.html'
    model = ApplicationStudent
    queryset = ApplicationStudent.objects.all()
    required_permissions = [settings.COORDINATION, ]

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_discursive_omr:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super(PrintDiscursiveAnswerSheetView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        questions = self.object.application.exam.questions.using('default').all().order_by(
            'examquestion__exam_teacher_subject__order', 'examquestion__order'
        ).distinct()

        for question in questions:
            question.in_last_questions = str(question in list(questions)[-4:]).lower()

        is_randomized = False
        version_number = self.request.GET.get('randomization_version', None)
        if version_number:
            randomization_version = RandomizationVersion.objects.filter(
                application_student=self.object,
                version_number=version_number,
            ).first()

            is_randomized = bool(randomization_version)

        qr_code_text = '{}:{}:{}'.format(
            f'R{version_number}' if is_randomized else 'S',
            OMRCategory.DISCURSIVE_025,
            self.object.pk
        )

        context['qr_code_text'] = qr_code_text
        context['application'] = self.object.application
        context['exam'] = self.object.application.exam
        context['questions'] = questions.availables(self.object.application.exam)
        context['split_subjects'] = self.request.GET.get('split_subjects', False)
        context['iterator'] = itertools.count()
        context['questions_categories'] = [Question.TEXTUAL, Question.FILE]
        context['application_randomization_version'] = []

        try:
            context['auto_correct_discursives'] = self.object.application.exam.coordinations.all().first().unity.client.has_discursive_auto_correction
        except:
            context['auto_correct_discursives'] = True
        
        return context


class PrintDetachedDiscursiveAnswerSheetView(LoginOrTokenRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'omr/export_discursive_answer_sheet.html'
    model = Application
    queryset = Application.objects.all()
    required_permissions = [settings.COORDINATION, ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        questions = self.object.exam.questions.using('default').all().order_by(
            'examquestion__exam_teacher_subject__order', 'examquestion__order'
        ).distinct()

        for question in questions:
            question.in_last_questions = str(question in list(questions)[-4:]).lower()

        context['qr_code_text'] = f'A:{OMRCategory.DISCURSIVE_025}:{self.object.pk}'
        context['application'] = self.object
        context['exam'] = self.object.exam
        context['questions'] = questions.availables(self.object.exam)
        context['hide_answer_lines'] = self.request.GET.get('hide_answer_lines', False)
        context['split_subjects'] = self.request.GET.get('split_subjects', False)
        context["iterator"] = itertools.count()
        context['questions_categories'] = [Question.TEXTUAL, Question.FILE]
        context['application_randomization_version'] = []

        try:
            context['auto_correct_discursives'] = self.object.exam.coordinations.all().first().unity.client.has_discursive_auto_correction
        except:
            context['auto_correct_discursives'] = True
        
        return context


class PrintDetachedEssayAnswerSheet(LoginOrTokenRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'omr/mockups/answer_sheet_essay.html'
    model = Application
    queryset = Application.objects.all()
    required_permissions = [settings.COORDINATION, ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        exam_question = ExamQuestion.objects.filter(
            exam=self.object.exam,
            question__is_essay=True
        ).availables(self.object.exam).first()

        context['qr_code_text'] = f'A:{OMRCategory.ESSAY_1}:{self.object.pk}'
        context['object'] = self.object
        context['client'] = self.object.students.all().first().client
        context['exam_question'] = exam_question
        context['is_draft'] = bool(self.request.GET.get('is_draft', False))
        context['is_detached'] = True
        return context
    
class PrintApplicationStudentEssayAnswerSheet(LoginOrTokenRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'omr/mockups/answer_sheet_essay.html'
    model = ApplicationStudent
    queryset = ApplicationStudent.objects.all()
    required_permissions = [settings.COORDINATION, ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        exam_question = ExamQuestion.objects.filter(
            exam=self.object.application.exam,
            question__is_essay=True
        ).availables(self.object.application.exam).first()

        context['qr_code_text'] = f'S:{OMRCategory.ESSAY_1}:{self.object.pk}'
        context['object'] = self.object.application
        context['application_student'] = self.object
        context['client'] = self.object.student.client
        context['exam_question'] = exam_question
        context['is_draft'] = bool(self.request.GET.get('is_draft', False))
        return context


class PrintPreviewDiscursiveAnswerSheetView(LoginOrTokenRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'omr/export_discursive_answer_sheet.html'
    model = Exam
    required_permissions = [settings.COORDINATION, ]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        questions = self.object.questions.using('default').all().order_by(
            'examquestion__exam_teacher_subject__order', 'examquestion__order'
        ).distinct()

        for question in questions:
            question.in_last_questions = str(question in list(questions)[-4:]).lower()

        context['qr_code_text'] = 'PRINT_PREVIEW'
        context['exam'] = self.object
        context['questions'] = questions.availables(self.object)
        context['hide_answer_lines'] = self.request.GET.get('hide_answer_lines', False)
        context['split_subjects'] = self.request.GET.get('split_subjects', False)
        context["iterator"] = itertools.count()
        context['questions_categories'] = [Question.TEXTUAL, Question.FILE]
        context['application_randomization_version'] = None

        try:
            context['auto_correct_discursives'] = self.object.exam.coordinations.all().first().unity.client.has_discursive_auto_correction
        except:
            context['auto_correct_discursives'] = True
        
        return context
    
class OMRCorrectionListView(LoginRequiredMixin, CheckHasPermission, ListView):
    template_name = 'omr/omr_correction.html'
    model = OMRUpload
    required_permissions = [settings.COORDINATION, ]
    paginate_by = 10
    
    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_omr:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('applications:applications_list'))

        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(corrected=False)
        
        if self.kwargs.get('pk', None):
            queryset = queryset.filter(pk=self.kwargs['pk'])
        
        if self.request.user.can_see_all():
            queryset = queryset.filter(
                user__coordination_member__coordination__unity__client__in=self.request.user.get_clients_cache()
            ).distinct().select_related('user').order_by('-created_at')
        else:
            queryset = queryset.filter(
                user__coordination_member__coordination__in=self.request.user.get_coordinations_cache()
            ).distinct().select_related('user').order_by('-created_at')

        if self.request.GET.get('q_coordination'):
            queryset = queryset.filter(user__coordination_member__coordination__in=self.request.GET.getlist('q_coordination'))
            
        if self.request.GET.get('q_exam'):
            queryset = queryset.filter(application_students__application__exam__name__icontains=self.request.GET.get('q_exam'))
            
        if self.request.GET.get('q_seen'):
            queryset = queryset.filter(seen=False)

        return queryset.filter(created_at__year=timezone.now().year).distinct()
    
    def get_context_data(self, **kwargs):
        from fiscallizeon.clients.models import SchoolCoordination
        context = super().get_context_data(**kwargs)
        context["q_coordination"] = self.request.GET.getlist('q_coordination', [])
        context["q_exam"] = self.request.GET.get('q_exam', '')
        context["q_seen"] = True if self.request.GET.get('q_seen') else False
        context["coordinations"] = SchoolCoordination.objects.filter(pk__in=self.request.user.get_coordinations_cache()) 
        return context


class PrintELITAvulseAnswerSheet(LoginOrTokenRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'omr/export_elit_answer_sheet.html'
    model = Application
    required_permissions = [settings.COORDINATION, ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_dettached'] = True
        context['application'] = self.object

        if student := self.object.students.first():
            context['client'] = student.client
            
        context['application_students'] = [
            {'pk': self.object.pk} for _ in range(8)]
        return context


class ExportELITAnswerSheetDetachedView(LoginRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = [settings.COORDINATION, ]

    def post(self, request, *args, **kwargs):
        try:
            application = Application.objects.get(pk=self.kwargs.get('pk'))

            print_url = reverse(
                'omr:print_detached_elit_answer_sheet',
                kwargs={'pk': application.pk}
            )

            data = {
                "url": settings.BASE_URL + print_url,
                "filename": f'detached_elit_{str(application.pk)}.pdf',
            }

            auth_token = get_service_account_oauth2_token(settings.PRINTING_SERVICE_BASE_URL)
            headers = {"Authorization": f"Bearer {auth_token}"}

            print_url = settings.PRINTING_SERVICE_BASE_URL + settings.PRINTING_SERVICE_PATH
            with get_session_retry().post(print_url, json=data, headers=headers, stream=True) as r:
                file = BytesIO(r.content)
                file.seek(0)

            exam_name_no_spaces = re.sub(r'[\s]+|/', '_', application.exam.name)
            exam_name_safe = re.sub(r'[^a-zA-Z0-9_]+', '', exam_name_no_spaces)

            response = HttpResponse(file, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Folha_de_Respostas_ELIT_Avulsa_{exam_name_safe}.pdf"'
            return response

        except Exception as e:
            logger = logging.getLogger('fiscallizeon')
            remote_address = self.request.META.get('HTTP_X_FORWARDED_FOR') or self.request.META.get('REMOTE_ADDR')
            logger.error(e, extra={
                'remote_address': remote_address,
                'user': self.request.user,
                'user_pk': self.request.user.pk,
            })


class PrintOffsetAnswerSheetView(LoginOrTokenRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'omr/answer_sheet_offset.html'
    required_permissions = [settings.COORDINATION, ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        client = Client.objects.get(pk=self.kwargs.get('pk'))

        context['exam_questions'] = range(1, 121)
        context['client'] = client
        context['qr_code_text'] = f'A:12:{client.pk}'
        return context
    

class PrintOffsetSchoolClassAnswerSheetView(LoginOrTokenRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'omr/answer_sheet_offset_schoolclass.html'
    required_permissions = [settings.COORDINATION, ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        client = Client.objects.get(pk=self.kwargs.get('pk'))
        total_questions = int(self.request.GET.get('total_questions', 10))

        context['exam_questions'] = range(1, total_questions + 1)
        context['client'] = client
        context['qr_code_text'] = f'A:13:{client.pk}'
        return context

class ExportOffsetAnswerSheetView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'omr/answer_sheet_offset.html'
    required_permissions = [settings.COORDINATION, ]
    permission_required = [
        'omr.export_offset_answer_sheet',
        'omr.export_offset_answer_sheet_schoolclass'
    ]

    def get(self, request, *args, **kwargs):
        try:
            client = self.request.user.get_clients().first()

            print_url = reverse(
                'omr:print_offset_answer_sheet',
                kwargs={'pk': client.pk}
            )
            if self.request.GET.get('is_schoolclass', None):
                print_url = reverse(
                    'omr:print_offset_answer_sheet_schoolclass',
                    kwargs={'pk': client.pk}
                )

            data = {
                "url": settings.BASE_URL + print_url,
                "filename": f'detached_offset_lize_{client.pk}.pdf',
            }

            print_url = settings.LOCAL_PRINTING_SERVICE_BASE_URL + settings.PRINTING_SERVICE_PATH
            with get_session_retry().post(print_url, json=data, stream=True) as r:
                file = BytesIO(r.content)
                file.seek(0)

            response = HttpResponse(file, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Folha_de_Respostas_Offset.pdf"'
            return response

        except Exception as e:
            logger = logging.getLogger('fiscallizeon')
            remote_address = self.request.META.get('HTTP_X_FORWARDED_FOR') or self.request.META.get('REMOTE_ADDR')
            logger.error(e, extra={
                'remote_address': remote_address,
                'user': self.request.user,
                'user_pk': self.request.user.pk,
            })


class PrintEfaiDetachedAnswerSheetView(LoginOrTokenRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'omr/mockups/answer_sheet_subjects.html'
    required_permissions = [settings.COORDINATION, ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        application = Application.objects.get(pk=self.kwargs.get('pk'))

        exam_questions = ExamQuestion.objects.filter(
            exam=application.exam,
            question__number_is_hidden=False,
            question__category=Question.CHOICE,
        ).availables()

        if application.exam.is_abstract:
            exam_questions = exam_questions.annotate(
                subject=F('question__subject__name')
            ).order_by('order')
        else:
            exam_json = get_exam_base_json(application.exam)
            exam_questions_list = convert_json_to_choice_exam_questions_list(exam_json)
            exam_questions_pks = [q['pk'] for q in exam_questions_list]

            exam_questions = exam_questions.get_ordered_pks(
                exam_questions_pks
            ).annotate(
                subject=F('exam_teacher_subject__teacher_subject__subject__name')
            )

        context['exam_questions'] = exam_questions
        context['qr_code_text'] = 'QR_CONTENT'
        context['object'] = application
        context['client'] = None
        return context


class ExportAnswerSheetReduceModel(LoginOrTokenRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'omr/mockups/answer_sheet_reduced_model.html'
    required_permissions = [settings.COORDINATION, ]
    model = Application 
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        application = Application.objects.get(pk="77be195c-7591-4ebe-9e66-3a937b588bc8")

        exam_questions = ExamQuestion.objects.filter(
            exam=application.exam,
            question__number_is_hidden=False,
            question__category=Question.CHOICE,
        ).availables()

        if application.exam.is_abstract:
            exam_questions = exam_questions.annotate(
                subject=F('question__subject__name')
            ).order_by('order')
        else:
            exam_json = get_exam_base_json(application.exam)
            exam_questions_list = convert_json_to_choice_exam_questions_list(exam_json)
            exam_questions_pks = [q['pk'] for q in exam_questions_list]

            exam_questions = exam_questions.get_ordered_pks(
                exam_questions_pks
            ).annotate(
                subject=F('exam_teacher_subject__teacher_subject__subject__name')
            )
        context['exam_questions'] = exam_questions
        context['qr_code_text'] = 'QR_CONTENT'
        context['object'] = application
        context['client'] = self.request.user.client
        return context


print_application_student_answer_sheet = PrintApplicationStudentAnswerSheetView.as_view()
print_detached_answer_sheet = PrintDetachedAnswerSheetView.as_view()
print_application_attendance_list = PrintApplicationAttendanceListView.as_view()

export_answer_sheet_reduce_model = ExportAnswerSheetReduceModel.as_view()


export_answer_sheet_application_detached = ExportAnswerSheetsDetachedView.as_view()
export_answer_sheet_discursive_detached = ExportDiscursiveAnswerSheetsDetachedView.as_view()
import_answer_sheets = ImportAnswerSheetsView.as_view()
api_import_answer_sheets = ImportAnswerSheetsApiView.as_view()
retry_import_answer_sheets = RetryImportAnswerSheetsView.as_view()
omr_upload_list = AnswerSheetsListView.as_view()
omr_upload_detail = OMRUploadDetailView.as_view()
omr_upload_fix = OMRuploadFixView.as_view()
omr_discursive_upload_fix = OMRDiscursiveUploadFixView.as_view()

template_list = TemplateListView.as_view()
template_create = TemplateCreateTemplateView.as_view()
template_update = TemplateUpdateView.as_view()
template_delete = TemplateDeleteView.as_view()

print_discursive_answer_sheet = PrintDiscursiveAnswerSheetView.as_view()
print_detached_discursive_answer_sheet = PrintDetachedDiscursiveAnswerSheetView.as_view()
print_preview_discursive_answer_sheet = PrintPreviewDiscursiveAnswerSheetView.as_view()