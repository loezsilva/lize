
from dis import dis
from email.utils import localtime
import itertools
from typing import Any
from uuid import uuid4

from decimal import Decimal
from django import http

from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.http.response import  HttpResponseRedirect
from fiscallizeon.clients.models import EducationSystem, Unity
from fiscallizeon.core.print_colors import *
from fiscallizeon.settings import BASE_URL
from datetime import date, timedelta
from django.conf import settings
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.core.cache import cache
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.db.models import Q, Count
from django.db.models.functions import Coalesce
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q, Count, F, Value, ExpressionWrapper, fields, Sum, Subquery, OuterRef, Case, When, DateTimeField
from django.contrib.postgres.expressions import ArraySubquery

from django.views.generic import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView
from fiscallizeon.core.utils import round_half_up
from fiscallizeon.core.api import CsrfExemptSessionAuthentication

from fiscallizeon.events.models import Event
from fiscallizeon.exams.models import Exam, ExamHeader, ExamQuestion, ClientCustomPage
from fiscallizeon.subjects.models import Subject
from fiscallizeon.questions.models import Question
from fiscallizeon.subjects.models import KnowledgeArea
from fiscallizeon.classes.models import Grade, SchoolClass
from fiscallizeon.applications.utils import start_application_student
from fiscallizeon.core.utils import (
    CheckHasPermission, format_value, percentage_value, percentage_formatted, _get_client_device
)
from fiscallizeon.applications.models import Application, ApplicationStudent, HashAccess, ApplicationType
from fiscallizeon.answers.models import OptionAnswer, RetryAnswer, TextualAnswer, FileAnswer, SumAnswer, SumAnswerQuestionOption
from fiscallizeon.applications.forms import ApplicationEditStudentsForm, ApplicationForm, ApplicationEditForm, ApplicationMultipleForm, ApplicationStudentImportForm
from fiscallizeon.core.views import DashboardCoordinationView
from django.core.paginator import Paginator

from fiscallizeon.notifications.models import Notification
from fiscallizeon.notifications.functions import get_and_create_notifications
import pytz
from fiscallizeon.applications.mixins import StudentCanViewResultsMixin
class ApplicationStudentListMixin(object):
    
    @staticmethod
    def get_only_schedules(queryset):
        
        today = timezone.localtime(timezone.now())
        
        queryset = queryset.annotate(
            exam_datetime_end = ExpressionWrapper(F('application__date') + F('application__end') + timedelta(hours=3), output_field=DateTimeField()),
            homework_datetime_end = ExpressionWrapper(F('application__date_end') + F('application__end') + timedelta(hours=3), output_field=DateTimeField())
        ).filter(
            Q(
                Q(application__release_result_at_end=True, end_time__isnull=True),
                Q(
                    Q(application__category=Application.HOMEWORK, homework_datetime_end__gt=today) |
                    Q(application__category=Application.MONITORIN_EXAM, exam_datetime_end__gt=today)
                )
            ) |
            Q(
                application__release_result_at_end=False,
                application__student_stats_permission_date__gt=today,
            )
        )
        
        return queryset.values_list('pk')
    
    def get_queryset(self, student=None):
        queryset = super().get_queryset()
        
        _student = student or self.request.user.student
        
        today = timezone.localtime(timezone.now())
        
        if self.request.GET.get('year'):
            queryset = queryset.filter(
                application__date__year=self.request.GET.get('year'),
            )
        else:
            queryset = queryset.filter(
                Q(application__date__year=today.year),
                Q(
                    Q(application__duplicate_application=False) |
                    Q(is_omr=True)
                )
            )
        
        if self.request.GET.get('category') == 'homework':
            queryset = queryset.filter(
                Q(application__category=Application.HOMEWORK), 
                Q(
                    Q(application__duplicate_application=False) |
                    Q(is_omr=True)
                )
            )
        else:
            queryset = queryset.exclude(application__category=Application.HOMEWORK)
        
        if self.request.GET.get('only_scheduled'):
            queryset = queryset.filter(pk__in=self.get_only_schedules(queryset))
        else:
            queryset = queryset.exclude(pk__in=self.get_only_schedules(queryset)).exclude(application__student_stats_permission_date__isnull=True)
        
        queryset = queryset.filter(
            Q(
                Q(application__show_result_only_for_started_application=True),
                Q(
                    Q(option_answers__isnull=False) |
                    Q(textual_answers__isnull=False) |
                    Q(file_answers__isnull=False)
                )
            ) |
            Q(application__show_result_only_for_started_application=False)
        )

        if self.request.GET.getlist('q_subjects', ""):
            queryset = queryset.filter(
                Q(
                    Q(
                        Q(application__exam__is_abstract=False),
                        Q(application__exam__teacher_subjects__subject__in=self.request.GET.getlist('q_subjects', ""))  
                    ) | 
                    Q(
                        Q(application__exam__is_abstract=True),
                        Q(application__exam__questions__subject__in=self.request.GET.getlist('q_subjects', ""))
                    ) 
                )
            )

        if self.request.GET.get('q_date'):
            queryset = queryset.filter(application__date= self.request.GET.get('q_date'))

        if self.request.GET.getlist('q_classes', ""):
            queryset = queryset.filter(
                application__school_classes__pk__in=self.request.GET.getlist('q_classes', "")
        )

        if _student:
            return queryset.filter(
                student=_student,
                application__exam__isnull=False,
            ).get_annotation_count_answers(only_total_grade=True, exclude_annuleds=True).order_by('-created_at').distinct()

        return ApplicationStudent.objects.none()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localtime(timezone.now())
        context['q_subjects'] = self.request.GET.getlist('q_subjects', "")
        context['q_date'] = self.request.GET.get('q_date', "")
        context['q_classes'] = self.request.GET.getlist('q_classes', "")

        list_filters = [context['q_subjects'], context['q_date'], context['q_classes']]

        context['count_filters'] = len(list_filters) - list_filters.count("")

        student = None
        if self.request.user.user_type == "student":
            student = self.request.user.student
        
        context['q_subjects'] = self.request.GET.getlist('q_subjects', "")
        context['q_date'] = self.request.GET.get('q_date', "")
        context['q_classes'] = self.request.GET.getlist('q_classes', "")
        list_filters = [context['q_subjects'], context['q_date'], context['q_classes']]
        context['count_filters'] = len(list_filters) - list_filters.count("")

        queryset = super().get_queryset()

        if self.request.GET.get('year'):
            queryset = queryset.filter(
                application__date__year=self.request.GET.get('year'),
            )
        else:
            queryset = queryset.filter(
                Q(application__date__year=today.year),
                Q(
                    Q(application__duplicate_application=False) |
                    Q(is_omr=True)
                )
            )
        
        if self.request.GET.get('category') == 'homework':
            queryset = queryset.filter(
                Q(application__category=Application.HOMEWORK), 
                Q(
                    Q(application__duplicate_application=False) |
                    Q(is_omr=True)
                )
            )
        else:
            queryset = queryset.exclude(application__category=Application.HOMEWORK)
            
        if self.request.GET.get('only_scheduled'):
            queryset = queryset.filter(pk__in=self.get_only_schedules(queryset))
        else:
            queryset = queryset.exclude(pk__in=self.get_only_schedules(queryset))
            
        queryset = queryset.filter(
            Q(
                Q(application__show_result_only_for_started_application=True),
                Q(
                    Q(option_answers__isnull=False) |
                    Q(textual_answers__isnull=False) |
                    Q(file_answers__isnull=False)
                )
            ) |
            Q(application__show_result_only_for_started_application=False)
        )
        if context['q_subjects']:
            queryset = queryset.filter(
                Q(
                    Q(
                        Q(application__exam__is_abstract=False),
                        Q(application__exam__teacher_subjects__subject__in=self.request.GET.getlist('q_subjects', ""))  
                    ) | 
                    Q(
                        Q(application__exam__is_abstract=True),
                        Q(application__exam__questions__subject__in=self.request.GET.getlist('q_subjects', ""))
                    ) 
                )
            )
            
        if context['q_classes']:
            queryset = queryset.filter(
                application__school_classes__pk__in=self.request.GET.getlist('q_classes', "")
        )

        if context['q_date']:
            queryset = queryset.filter(application__date=self.request.GET.get('q_date'))

        if student:
            queryset = queryset.filter(
                    student=student,
                    application__exam__isnull=False,
                ).get_annotation_count_answers(only_total_grade=True, exclude_annuleds=True).order_by('-created_at').distinct()

        context['applications'] = queryset
        
        context["today"] = today
        
        context['year'] = today.year
        context['only_scheduled'] = False

        context['is_mobile'] = self.request.user_agent.is_mobile
        
        if self.request.GET.get('page'):
            context['page'] = self.request.GET.get('page')
        else:
            context['page'] = 1
        
        if self.request.GET.get('year'):
            context['year'] = self.request.GET.get('year')
            
        if self.request.GET.get('only_scheduled'):
            context['only_scheduled'] = self.request.GET.get('only_scheduled')

        if self.request.GET.get('category'):
            context['category'] = self.request.GET.get('category')
        
        context['subjects'] = self.request.user.inspector.subjects.all() if self.request.user.user_type == "teacher" else Subject.objects.filter(
            Q(parent_subject__isnull=True) |
            Q(client__isnull=True) |
            Q(
                Q(parent_subject__isnull=False) &
                Q(client__in=self.request.user.get_clients_cache())
            )
        ).order_by('created_at').distinct('created_at', 'pk').values('pk', 'name', 'knowledge_area__name')
        context['classes'] = SchoolClass.objects.filter(
            Q(
                Q(coordination__in=self.request.user.get_coordinations()),
                 Q(students=student),
                 Q(school_year=context['year'])
            )
        ).distinct('created_at', 'pk').order_by('-created_at').values('pk', 'name', 'coordination__unity__name',  'school_year')

        return context

class ApplicationStudentListView(LoginRequiredMixin, CheckHasPermission, ApplicationStudentListMixin, ListView):
    template_name = 'dashboard/applications/application_student_list.html'
    required_permissions = [settings.STUDENT, ]
    model = ApplicationStudent
    paginate_by = 10  
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if user.is_authenticated and user.get_clients().first().type_client == 3:
            return redirect(reverse('applications:mentorize_application_student_list'))
        return super().dispatch(request, *args, **kwargs)
    

class ApplicationStudentDetailView(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'dashboard/applications/application_student_detail.html'
    required_permissions = [settings.STUDENT, ]
    model = ApplicationStudent

class ApplicationListView(LoginRequiredMixin, CheckHasPermission, ListView):
    template_name = 'dashboard/applications/application_list_new.html'
    required_permissions = [settings.COORDINATION, settings.TEACHER]

    model = Application
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if not user.is_authenticated or user.user_type == settings.TEACHER and not user.client_teachers_can_elaborate_exam:
            messages.error(self.request, 'Você não tem permissão para acessar esta página')
            return redirect(reverse('core:redirect_dashboard'))

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        today = timezone.localtime(timezone.now())

        queryset = Application.objects.filter(
            Q(
                Q(exam__coordinations__in=self.request.user.get_coordinations())
			),
        ).exclude(automatic_creation=True).order_by('-created_at')

        if self.request.user.user_type == settings.TEACHER:
            queryset = queryset.filter(
                exam__created_by=self.request.user
            )

        if self.request.GET.get('year'):
            queryset = queryset.filter(
                date__year=self.request.GET.get('year'),
            )
        else:
            queryset = queryset.filter(
                date__year=today.year,
            )
            
        if self.request.GET.get('category') and (self.request.user.client_has_exam_elaboration or self.request.user.client_allow_online_abstract_application):
            category = self.request.GET.get('category')
            if category == 'online':
                queryset = queryset.filter(
                    category=Application.MONITORIN_EXAM
                )
            if category == 'homework':
                queryset = queryset.filter(
                    category=Application.HOMEWORK
                )
            elif category == 'presential':
                queryset = queryset.filter(
                    category=Application.PRESENTIAL
                )
        else:
            if not self.request.user.client_has_exam_elaboration:
                queryset = queryset.filter(
                    category=Application.PRESENTIAL
                )


        if self.request.GET.get('q_pk', ''):
            queryset = queryset.filter(pk=self.request.GET.get('q_pk', ''))

        if self.request.GET.get('q_name'):
            
            query_terms = [Q(exam__name__unaccent__icontains=term) for term in self.request.GET.get('q_name').split(' ')]
            query = Q()
            for quey in query_terms:
                query &= quey

            queryset = queryset.filter(
                query
            )
        

        if self.request.GET.get('q_initial_date') and not self.request.GET.get('q_final_date'):
            queryset = queryset.filter(
                date=self.request.GET.get('q_initial_date')
            ).order_by('date', 'start')
        
        if self.request.GET.get('q_final_date') and not self.request.GET.get('q_initial_date'):
            queryset = queryset.filter(
                date__lte=self.request.GET.get('q_final_date')
            ).order_by('date', 'start')

        if self.request.GET.get('q_initial_date') and self.request.GET.get('q_final_date'):
            queryset = queryset.filter(date__gte=self.request.GET.get('q_initial_date', today), date__lte=self.request.GET.get('q_final_date', today)).order_by('date', 'start')
            
        if self.request.GET.getlist('q_subjects', ""):
            queryset = queryset.filter(
                Q(
                    Q(
                        Q(exam__is_abstract=False),
                        Q(exam__teacher_subjects__subject__in=self.request.GET.getlist('q_subjects', ""))  
                    ) | 
                    Q(
                        Q(exam__is_abstract=True),
                        Q(exam__questions__subject__in=self.request.GET.getlist('q_subjects', ""))
                    ) 
                )
            )

        if self.request.GET.getlist('q_classes', ""):
            queryset = queryset.filter(
                school_classes__pk__in=self.request.GET.getlist('q_classes', "")
            )

        if self.request.GET.getlist('q_grades', ""):
            queryset = queryset.filter(
                Q(
                    Q(
                        Q(exam__is_abstract=False),
                        Q(exam__examteachersubject__grade__in=self.request.GET.getlist('q_grades', ""))  
                    ) | 
                    Q(
                        Q(exam__is_abstract=True),
                        Q(exam__questions__grade__in=self.request.GET.getlist('q_grades', ""))
                    ) 
                )
            )

        if applications_types := self.request.GET.getlist('q_application_type', ""):
            
            queryset = queryset.filter(
                application_type__in=applications_types
            ) 

        if self.request.GET.getlist('q_units', ""):
            queryset = queryset.filter(
                exam__coordinations__unity__in=self.request.GET.getlist('q_units', "")
            )

        if self.request.GET.get('q_already_disclosed', ""):
            queryset = queryset.filter(
                student_stats_permission_date__lte=today
            )

        if self.request.GET.get('q_no_disclosed', ""):
            queryset = queryset.filter(
                student_stats_permission_date__gt=today
            )
            
        if self.request.GET.get('q_date', ""):
            queryset = queryset.order_by('start')

        if self.request.GET.get('q_is_print_ready', ""):
            queryset = queryset.filter(
                print_ready=True
            )

        if self.request.GET.get('q_has_answer_sheet', ""):
            queryset = queryset.exclude(
                Q(
                    Q(answer_sheet__isnull=True) |
                    Q(answer_sheet="")

                )
            )

        return queryset.distinct()
        
    def get_context_data(self, **kwargs):
        context = super(ApplicationListView, self).get_context_data(**kwargs)
        context['q_is_print_ready'] = self.request.GET.get('q_is_print_ready', "")
        context['q_has_answer_sheet'] = self.request.GET.get('q_has_answer_sheet', "")
        context['page'] = self.request.GET.get('page', "")
        context['q_pk'] = self.request.GET.get('q_pk', '')
        context['q_name'] = self.request.GET.get('q_name', "")
        context['q_initial_date'] = self.request.GET.get('q_initial_date', "")
        context['q_final_date'] = self.request.GET.get('q_final_date', "")
        context['q_subjects'] = self.request.GET.getlist('q_subjects', "")
        context['q_classes'] = self.request.GET.get('q_classes', "")
        context['q_grades'] = self.request.GET.get('q_grades', "")
        context['q_units'] = self.request.GET.getlist('q_units', "")
        context['q_already_disclosed'] = self.request.GET.get('q_already_disclosed', "")
        context['q_no_disclosed'] = self.request.GET.get('q_no_disclosed', "")
        context['q_application_type'] = self.request.GET.getlist('q_application_type', "")
        context['category'] = self.request.GET.get('category', '') if self.request.user.client_has_exam_elaboration else ''
        context['has_discursives'] = self.request.user.get_clients().filter(has_discursive_answers=True).exists()
        context['exam_headers'] = ExamHeader.objects.filter(
            user__coordination_member__coordination__unity__client__in=self.request.user.get_clients_cache()
        ).distinct()
        
        context['exam_custom_pages'] = ClientCustomPage.objects.filter(
            client__in=self.request.user.get_clients_cache()
        ).distinct()
        
        list_filters = [context['q_name'], context['q_initial_date'], context['q_final_date'], context['q_subjects'], context["q_classes"], context["q_grades"], context['q_already_disclosed'], context['q_no_disclosed'], context['category'], context['q_is_print_ready'], context['q_has_answer_sheet'], context['q_application_type']]

        context['count_filters'] = len(list_filters) - list_filters.count("")

        today = timezone.localtime(timezone.now())
        
        context['classes'] = SchoolClass.objects.filter(
            Q(
				Q(coordination__in=self.request.user.get_coordinations())
			)
        ).distinct('created_at', 'pk').order_by('-created_at').values('pk', 'name', 'coordination__unity__name',  'school_year')

        context['subjects'] = self.request.user.inspector.subjects.all() if self.request.user.user_type == "teacher" else Subject.objects.filter(
            Q(parent_subject__isnull=True) |
            Q(client__isnull=True) |
            Q(
                Q(parent_subject__isnull=False) &
                Q(client__in=self.request.user.get_clients_cache())
            )
        ).order_by('created_at').distinct('created_at', 'pk').values('pk', 'name', 'knowledge_area__name')

        context['today'] = today

        user = self.request.user

        filter_condition = Q()
        if user.has_high_school_coordinations:
            filter_condition |= Q(level=Grade.HIGHT_SCHOOL)

        if user.has_elementary_school_only_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL)

        if user.has_elementary_school2_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL_2)

        context["grades"] = Grade.objects.filter(filter_condition)
        context["units"] = Unity.objects.filter(client__in=self.request.user.get_clients())
        
        context['year'] = today.year
        if self.request.GET.get('year'):
            context['year'] = self.request.GET.get('year')

        if user.client_has_customize_application:
            context['application_type_options'] = ApplicationType.objects.filter(client=user.client).order_by('name')

        return context


class ApplicationMonitoringListView(DashboardCoordinationView):
    template_name = 'dashboard/applications/application_monitoring.html'


class ApplicationCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    template_name = 'dashboard/applications/application_create_update.html'
    model = Application
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    form_class = ApplicationForm
    permission_required = 'applications.add_application'
    success_message = 'Aplicação cadastrada com sucesso'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        filter_condition = Q()
        if user.has_high_school_coordinations:
            filter_condition |= Q(level=Grade.HIGHT_SCHOOL)

        if user.has_elementary_school_only_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL)

        if user.has_elementary_school2_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL_2)

        context["grades"] = Grade.objects.filter(filter_condition)

        context['MIN_MINUTES_CREATE_BEFORE_START'] = settings.MIN_MINUTES_CREATE_BEFORE_START

        context["education_systems"] = EducationSystem.objects.filter(client__in=user.get_clients_cache())
        
        has_turn = SchoolClass.objects.filter(coordination__in=user.get_coordinations_cache(), turn__isnull=False).count()
        
        if has_turn:
            context["turns"] = SchoolClass.COURSE_TYPE_CHOICE
        
        unities = Unity.objects.filter(
            coordinations__in=user.get_coordinations_cache()
        ).distinct()
        
        context["unities"] = unities
        
        if self.request.GET.get('exam_template'):
            context["exam_template"] = Exam.objects.using('default').get(pk=self.request.GET.get('exam_template'))

        today = timezone.localtime(timezone.now())
        
        if self.request.GET.get('year'):
            context['year'] = self.request.GET.get('year')
        else:
            context['year'] = today.year
        
        if self.request.GET.get('exam'):
            context["exam"] = Exam.objects.using('default').get(pk=self.request.GET.get('exam'))

        if self.request.GET.get('category'):
            context['category'] = self.request.GET.get('category')

        return context

    def form_valid(self, form):
        form.save(commit=True)
        if self.request.POST.get('create_distribution'):
            return HttpResponseRedirect(f"{reverse('distribution:distribution_create')}?application_id={form.instance.pk}")
        
        return super(ApplicationCreateView, self).form_valid(form)
    
    def form_invalid(self, form):
        return super().form_invalid(form)
        
    def get_success_url(self):

        url = reverse('applications:applications_list')
        
        get_and_create_notifications(view=self, trigger=Notification.AFTER_CREATE)
        
        if self.object.category == Application.PRESENTIAL:
            url += '?category=presential'
        elif self.object.category == Application.HOMEWORK:
            url += '?category=homework'
        
        return url

class ApplicationCreateMultipleView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    template_name = 'dashboard/applications/application_create_update.html'
    model = Application
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    form_class = ApplicationMultipleForm
    permission_required = 'applications.add_application'
    success_message = 'Aplicações cadastradas com sucesso!'
    nps_app_label = "ApplicationMultiple"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        
        context['multiple'] = True

        context['MIN_MINUTES_CREATE_BEFORE_START'] = settings.MIN_MINUTES_CREATE_BEFORE_START

        filter_condition = Q()
        if user.has_high_school_coordinations:
            filter_condition |= Q(level=Grade.HIGHT_SCHOOL)

        if user.has_elementary_school_only_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL)

        if user.has_elementary_school2_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL_2)

        context["grades"] = Grade.objects.filter(filter_condition)

        context["education_systems"] = EducationSystem.objects.filter(client__in=user.get_clients_cache())
        
        has_turn = SchoolClass.objects.filter(coordination__in=user.get_coordinations_cache(), turn__isnull=False).count()
        
        if has_turn:
            context["turns"] = SchoolClass.COURSE_TYPE_CHOICE
        
        unities = Unity.objects.filter(
            coordinations__in=user.get_coordinations_cache()
        ).distinct()
        
        context["unities"] = unities
        
        if self.request.GET.get('exam_template'):
            context["exam_template"] = Exam.objects.using('default').get(pk=self.request.GET.get('exam_template'))

        today = timezone.localtime(timezone.now())
        
        if self.request.GET.get('year'):
            context['year'] = self.request.GET.get('year')
        else:
            context['year'] = today.year
        
        if self.request.GET.get('exam'):
            context["exam"] = Exam.objects.using('default').get(pk=self.request.GET.get('exam'))

        if self.request.GET.get('category'):
            context['category'] = self.request.GET.get('category')

        return context
    
    def form_invalid(self, form):
        
        print("###### ", form.errors)
        
        return super().form_invalid(form)

    def form_valid(self, form):

        user = self.request.user

        release_result_at_end = self.request.POST.get('release_result_at_end')

        exams = self.request.POST.getlist('exam')
        dates = self.request.POST.getlist('date')
        starts = self.request.POST.getlist('start')
        ends = self.request.POST.getlist('end')
        end_dates = self.request.POST.getlist('date_end')
        student_stats_permission_dates = self.request.POST.getlist('student_stats_permission_date')
        deadline_to_request_reviews = self.request.POST.getlist('deadline_to_request_review')
        deadline_for_correction_of_responses = self.request.POST.getlist('deadline_for_correction_of_responses')

        with transaction.atomic():
            for index, exam in enumerate(exams):
                application_instance = form.save(commit=False)
                
                exam_instance = Exam.objects.using('default').get(pk=exam)
                application_instance.pk = uuid4()
                
                application_instance.exam = exam_instance
                application_instance.date = dates[index]

                if end_dates:
                    application_instance.date_end = end_dates[index]    
                application_instance.start = starts[index]

                application_instance.end = ends[index]

                if not release_result_at_end and student_stats_permission_dates[index] != '':
                    application_instance.student_stats_permission_date = student_stats_permission_dates[index]
                
                if user.client_has_wrongs:
                    if deadline_to_request_reviews[index] != '':
                        application_instance.deadline_to_request_review = deadline_to_request_reviews[index]

                if deadline_for_correction_of_responses[index] != '':
                    application_instance.deadline_for_correction_of_responses = deadline_for_correction_of_responses[index]
                
                application_instance.save()

                form.save_m2m()
        
        return super().form_valid(form)
        
    def get_success_url(self):

        url = reverse('applications:applications_list')
        
        get_and_create_notifications(view=self, trigger=Notification.AFTER_CREATE)
        
        if self.object.category == Application.PRESENTIAL:
            url += '?category=presential'
        elif self.object.category == Application.HOMEWORK:
            url += '?category=homework'
        
        return url
class ApplicationUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    template_name = 'dashboard/applications/application_create_update.html'
    model = Application
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    form_class = ApplicationEditForm
    permission_required = 'applications.change_application'
    success_message = 'Aplicação atualizada com sucesso'

    def dispatch(self, request, *args, **kwargs):
        application = self.get_object()
        user = self.request.user
        if not user.is_authenticated or user.user_type == settings.TEACHER and (not application.exam.created_by == user or not user.client_teachers_can_elaborate_exam):
            messages.error(self.request, 'Você não tem permissão para editar esta aplicação')
            return redirect(reverse('core:redirect_dashboard'))

        return super().dispatch(request, *args, **kwargs)
    
    
    def get_success_url(self):
        get_and_create_notifications(view=self, trigger=Notification.AFTER_UPDATE)
        return f'{reverse("applications:applications_list")}?{self.request.META.get("QUERY_STRING", None)}'


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.localtime(timezone.now())
        applications_students = self.get_object().applicationstudent_set.all()
        context['applications_students'] = applications_students
        
        if self.request.GET.get('year'):
            context['year'] = self.request.GET.get('year')
        else:
            context['year'] = today.year

        context['MIN_MINUTES_CREATE_BEFORE_START'] = settings.MIN_MINUTES_CREATE_BEFORE_START

        return context
        
    
    def form_invalid(self, form: ApplicationEditForm):
        print("######", form.errors)
        return super(ApplicationUpdateView, self).form_invalid(form)

class ApplicationDiscloseUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    template_name = 'dashboard/applications/application_update.html'
    model = Application
    required_permissions = [settings.COORDINATION, ]
    fields = ['student_stats_permission_date']
    permission_required = 'applications.can_disclose_application',
    success_message = 'Resultado de aplicação divulgado com sucesso.'
    
    def get_success_url(self):
        self.object.student_stats_permission_date = date.today()
        self.object.save()

        return self.request.META.get('HTTP_REFERER', None)

class ApplicationDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = Application
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    permission_required = 'applications.delete_application'
    success_message = "Aplicação removida com sucesso!"

    def dispatch(self, request, *args, **kwargs):
        application = self.get_object()
        user = self.request.user
        if not user.is_authenticated or user.user_type == settings.TEACHER and (not application.exam.created_by == user or not user.client_teachers_can_elaborate_exam):
            messages.error(self.request, 'Você não tem permissão para remover esta aplicação')
            return redirect(reverse('core:redirect_dashboard'))
            
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            self.object.delete()
            messages.success(self.request, self.success_message)
            
        except ProtectedError:
            messages.error(self.request, "Ocorreu um erro ao remover, não é possível remover aplicações que houve participação de alunos.")
            
        return HttpResponseRedirect(self.get_success_url())  
    
    def get_success_url(self):
        get_and_create_notifications(view=self, trigger=Notification.AFTER_DELETE)
        return self.request.META.get('HTTP_REFERER', None)

class ApplicationMonitoringInspectorView(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'dashboard/monitoring/inspector/inspector-new.html'
    required_permissions = [settings.COORDINATION, settings.INSPECTOR, settings.TEACHER]
    model = Application

    def dispatch(self, request, *args, **kwargs):		
        if not self.get_object().can_be_opened:
            messages.warning(request, "O ambiente dessa aplicação está sendo preparado ou já foi finalizado.")
            return redirect("core:redirect_dashboard")

        return super(ApplicationMonitoringInspectorView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ApplicationMonitoringInspectorView, self).get_context_data(**kwargs)
        context["students"] = ApplicationStudent.objects.filter(
            application=self.object,
            student__in=self.object.students.all()
        ).distinct()
        context['disable_support_chat'] = True
        
        return context

class ClearAllAnswersAndRedirectView(LoginRequiredMixin, CheckHasPermission, UpdateView):
    model = ApplicationStudent
    authentication_classes = (CsrfExemptSessionAuthentication, )
    required_permissions = [settings.STUDENT, ]

    def post(self, request, *args, **kwargs):
        application_student = self.get_object()
        application_student.start_time = None
        application_student.end_time = None
        application_student.save()

        with transaction.atomic():            
            OptionAnswer.objects.filter(student_application=application_student).delete()
            
            TextualAnswer.objects.filter(student_application=application_student).delete()
            
            SumAnswer.objects.filter(student_application=application_student).delete()
            
            FileAnswer.objects.filter(student_application=application_student).delete()
            

        redirect_url = reverse('applications:applications_homework_student', kwargs={'pk': application_student.pk})
        redirect_url += f'?cache_clear={True}'
        
        return JsonResponse({'redirect_url': redirect_url})
    
class ApplicationMonitoringStudentView(LoginRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = [settings.STUDENT, ]
    model = ApplicationStudent
    QUESTION_CACHE_TIME = 300
    is_late = False

    def get_template_names(self):
        application_student = self.get_object()

        if application_student.application.exam.is_abstract:
            return ['dashboard/monitoring/student/student-new-exam-abstract.html']
        else:
            return ['dashboard/monitoring/student/student-new-exam.html']

    def get_object(self):
        return get_object_or_404(ApplicationStudent.objects.using('default'), pk=self.kwargs.get('pk'))

    def dispatch(self, request, *args, **kwargs):	
        application_student = self.get_object()

        if request.user != self.get_object().student.user:
            messages.error(request, "Você não tem permissão para acessar essa prova. Tente novamente.")
            return redirect("core:redirect_dashboard") 
        
        # Verifica se o token já foi respondido
        if application_student.application.token_online and not request.session.get(f'token_from_application_{application_student.application.pk}'):
            messages.error(request, "Você precisa responder o token para essa applicação. Tente novamente.")
            return redirect("core:redirect_dashboard")

        if application_student.is_blocked_by_tolerance:
            messages.error(request, "Você não pode iniciar essa prova.")
            return redirect("core:redirect_dashboard")

        if application_student.start_time and application_student.end_time and not application_student.application.allow_student_redo_list:
            messages.warning(request, "Você já finalizou essa aplicação.")
            return redirect("core:redirect_dashboard")

        if not application_student.application.can_be_opened and not application_student.student_released_for_custom_time:
            messages.error(request, "O ambiente dessa aplicação está sendo preparado ou já foi finalizado.")
            return redirect("core:redirect_dashboard")
        
        self.is_late = (application_student.application_state == "waiting" and application_student.is_tolerance_reached) or (application_student.application_state == "started" and application_student.start_time > application_student.start_time_tolerance and not application_student.justification_delay)

        start_application = start_application_student(application_student, self.request)

        return super(ApplicationMonitoringStudentView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ApplicationMonitoringStudentView, self).get_context_data(**kwargs)
        application_student = self.object

        context['BASE_URL'] = BASE_URL 
        questions = cache.get(f'QUESTIONS_{str(self.object.application.exam.pk)}')
        
        if not questions:
            questions =  application_student.application.exam.generate_exam_questions_cache()       
            

        if application_student.start_time:
            choice_answers = list(OptionAnswer.objects.using('default').filter(
                                    status=OptionAnswer.ACTIVE,
                                    student_application=application_student
                                ).annotate(
                                    question=F('question_option__question'), 
                                    pk=F('question_option__pk'),
                                    content=Value(''),
                                    qrcode=Value(False),
                                    sum_question_options_checked=Value(''),
                                    value=Value(0),
                                ).order_by('-created_at').values('question', 'pk', 'content', 'sum_question_options_checked', 'value', 'qrcode', 'created_at'))
            
            sum_answers = list(SumAnswer.objects.filter(
                                student_application=application_student,
                            ).annotate(
                                sum_question_options_checked=
                                    ArraySubquery(
                                            SumAnswerQuestionOption.objects.filter(
                                                sum_answer=OuterRef("pk"), 
                                                checked=True,
                                            ).values("question_option__pk")
                                    ),
                                content=Value(''),
                                qrcode=Value(False),
                            ).order_by('-created_at').values(
                                'id', 'question','pk', 'content', 'sum_question_options_checked', 'value', 'qrcode', 'created_at'
                            )
                        )

            textual_answers = list(TextualAnswer.objects.using('default').filter(
                                    student_application=application_student
                                ).annotate(
                                    qrcode=Value(False),
                                    sum_question_options_checked=Value(''),
                                    value=Value(0),
                                ).values('question', 'pk', 'content',  'sum_question_options_checked', 'value', 'qrcode', 'created_at').order_by(
                                    '-created_at'
                                ))

            file_answers = list(FileAnswer.objects.using('default').filter(
                                    student_application=application_student
                                ).annotate(
                                    content=F('arquivo'),
                                    qrcode=F('send_on_qrcode'),
                                    sum_question_options_checked=Value(''),
                                    value=Value(0),
                                ).order_by('-created_at').values(
                                    'question', 'pk', 'content','sum_question_options_checked', 'value', 'qrcode', 'created_at'
                                ))
            answers = choice_answers + textual_answers + file_answers + sum_answers

            for question in list(questions):
                answer = list(filter(lambda ans: ans['question'] == question.pk, answers))
                if question.category != Question.SUM_QUESTION:
                    question.answer_id = answer[-1]['pk'] if answer else ''              
                question.answer_content = answer[-1]['content'] if answer else ''
                question.send_on_qrcode = answer[-1]['qrcode'] if answer else ''
                question.answer_time = answer[-1]['created_at'] if answer else ''
                question.sum_question_options_checked = [str(option_id) for option_id in (answer[-1]['sum_question_options_checked'] if answer else [])]
                question.values = int(answer[-1]['value']) if answer and answer[-1]['value'] else 0

        context['questions'] = questions
        context["iterator"] = itertools.count(start=1)
        context["number_print_iterator"] = itertools.count(start=1)
        context['is_late'] = self.is_late
        context['disable_support_chat'] = True
        if application_student.application.exam.is_english_spanish and not application_student.foreign_language in [0, 1]:
            context['need_choose_language'] = True

        return context

class ApplicationHomeWorkStudentView(LoginRequiredMixin, CheckHasPermission, DetailView):
    required_permissions = [settings.STUDENT, ]
    model = ApplicationStudent
    QUESTION_CACHE_TIME = 300
    is_late = False

    def get_template_names(self):
        application_student = self.get_object()
        if application_student.application.exam.is_abstract:
            return ['dashboard/homeworks/student/student-homework-abstract.html']
        else:
            return ['dashboard/homeworks/student/student-homework.html']

    def get_object(self):
        return get_object_or_404(ApplicationStudent.objects.using('default'), pk=self.kwargs.get('pk'))

    def dispatch(self, request, *args, **kwargs):	
        application_student = self.get_object()

        if request.user != self.get_object().student.user:
            messages.error(request, "Você não tem permissão para acessar essa prova. Tente novamente.")
            return redirect("core:redirect_dashboard") 

        if application_student.start_time and application_student.end_time:
            messages.warning(request, "Você já finalizou essa aplicação.")
            return redirect("core:redirect_dashboard")

        if not application_student.application.can_be_opened and not application_student.student_released_for_custom_time:
            messages.error(request, "O ambiente dessa aplicação está sendo preparado ou já foi finalizado.")
            return redirect("core:redirect_dashboard")

        if application_student.already_reached_max_time_finish:
            messages.error(request, "O tempo máximo para finalizar essa lista de exercício foi atingido.")
            return redirect("core:redirect_dashboard")
        
        self.is_late = (application_student.application_state == "waiting" and application_student.is_tolerance_reached) or (application_student.application_state == "started" and application_student.start_time > application_student.start_time_tolerance and not application_student.justification_delay)

        start_application = start_application_student(application_student, self.request)

        return super(ApplicationHomeWorkStudentView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ApplicationHomeWorkStudentView, self).get_context_data(**kwargs)
        application_student = self.object

        context['BASE_URL'] = BASE_URL 
        questions = cache.get(f'QUESTIONS_{str(self.object.application.exam.pk)}')
        
        if not questions:
            questions =  application_student.application.exam.generate_exam_questions_cache()       
            

        if application_student.start_time:
            choice_answers = list(OptionAnswer.objects.using('default').filter(
                                    status=OptionAnswer.ACTIVE,
                                    student_application=application_student
                                ).annotate(
                                    question=F('question_option__question'), 
                                    pk=F('question_option__pk'),
                                    content=Value(''),
                                    qrcode=Value(False),
                                    sum_question_options_checked=Value(''),
                                    value=Value(0),
                                ).order_by('-created_at').values('pk', 'question', 'content', 'sum_question_options_checked', 'value', 'qrcode', 'created_at'))

            sum_answers = list(
                            SumAnswer.objects.filter(
                                student_application=application_student
                            ).annotate(
                                sum_question_options_checked=
                                    ArraySubquery(
                                            SumAnswerQuestionOption.objects.filter(
                                                sum_answer=OuterRef("pk"), 
                                                checked=True,
                                            ).values("question_option__pk")
                                    ),
                                content=Value(''),
                                qrcode=Value(False),
                            ).order_by('-created_at').values(
                                'id', 'question','pk', 'content', 'sum_question_options_checked', 'value', 'qrcode', 'created_at'
                            )
                        
            )
            textual_answers = list(TextualAnswer.objects.using('default').filter(
                                    student_application=application_student
                                ).annotate(
                                    qrcode=Value(False),
                                    sum_question_options_checked=Value(''),
                                    value=Value(0)
                                ).order_by('-created_at').values('pk', 'question', 'content', 'sum_question_options_checked', 'value','qrcode', 'created_at'))

            file_answers = list(FileAnswer.objects.using('default').filter(
                                    student_application=application_student
                                ).annotate(
                                    content=F('arquivo'),
                                    qrcode=F('send_on_qrcode'),
                                    sum_question_options_checked=Value(''),
                                    value=Value(0),
                                ).order_by('-created_at').values('pk', 'question', 'content',  'sum_question_options_checked', 'value','qrcode', 'created_at'))

            answers = choice_answers + textual_answers + file_answers + sum_answers
            for question in list(questions):
                answer = list(filter(lambda ans: ans['question'] == question.pk, answers))
                if question.category != Question.SUM_QUESTION:
                    question.answer_id = answer[-1]['pk'] if answer else ''              
                question.answer_content = answer[-1]['content'] if answer else ''
                question.send_on_qrcode = answer[-1]['qrcode'] if answer else ''
                question.answer_time = answer[-1]['created_at'] if answer else ''
                question.sum_question_options_checked = [str(option_id) for option_id in (answer[-1]['sum_question_options_checked'] if answer else [])]
                question.values = int(answer[-1]['value']) if answer and answer[-1]['value'] else 0

        context['questions'] = questions
        context["iterator"] = itertools.count(start=1)
        context["number_print_iterator"] = itertools.count(start=1)
        context['is_late'] = self.is_late
        context['disable_support_chat'] = True
        
        if application_student.application.exam.is_english_spanish and not application_student.foreign_language in [0, 1]:
            context['need_choose_language'] = True
            
        return context

class ApplicationOrientationsStudentView(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'dashboard/monitoring/student/orientations-students.html'
    required_permissions = [settings.STUDENT, ]
    model = ApplicationStudent

    def get_object(self):
        return get_object_or_404(ApplicationStudent.objects.using('default'), pk=self.kwargs.get('pk'))

    def dispatch(self, request, *args, **kwargs):
        device = _get_client_device(request)
        application_student = self.get_object()
        
        if application_student.is_blocked_by_tolerance:
            messages.error(request, "Você não pode iniciar essa prova.")
            return redirect("core:redirect_dashboard")

        if not application_student.can_be_started_device(device):
            messages.error(request, "Você não pode iniciar essa prova neste tipo de dispositivo.")

            return redirect("core:redirect_dashboard")

        if not application_student.application.can_be_opened:
            messages.error(request, "O ambiente dessa aplicação está sendo preparado ou já foi finalizado.")
            
            return redirect("core:redirect_dashboard")

        return super(ApplicationOrientationsStudentView, self).dispatch(request, *args, **kwargs)

class ApplicationDetailView(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'dashboard/applications/application_detail.html'
    model = Application
    required_permissions = [settings.COORDINATION, settings.TEACHER]

    def dispatch(self, request, *args, **kwargs):
        application = self.get_object()
        user = self.request.user
        if not user.is_authenticated or user.user_type == settings.TEACHER and (not application.exam.created_by == user or not user.client_teachers_can_elaborate_exam):
            messages.error(self.request, 'Você não tem permissão para ver detalhes desta aplicação')
            return redirect(reverse('core:redirect_dashboard'))
            
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        coordinations = user.get_coordinations_cache()
        
        application: Application = self.get_object()
        
        duration = ExpressionWrapper(F('end_time') - F('start_time'), output_field=fields.DurationField())

        students = application.applicationstudent_set.all().annotate(
            pauses=Count('events', filter=Q(events__event_type=Event.BATHROOM))
        ).annotate(
            exits_student=Count('events', filter=Q(events__event_type=Event.LEAVE_TAB))
        ).annotate(
            notes=Count('annotations')
        ).annotate(
            duration=duration 
        ).distinct()

        orderby = self.request.GET.get('orderby', '')

        if orderby:
            students = students.order_by(orderby)

        if q_student_name := self.request.GET.get('q_student_name', ''):
            students = students.filter(
                Q(
                    Q(student__name__icontains=q_student_name) |
                    Q(student__email__icontains=q_student_name)
                )
            )

        page = self.request.GET.get('page')
        students = Paginator(students, 30)

        students_different_exit_application = Event.objects.filter(student_application__in=application.applicationstudent_set.all()).values_list('student_application', flat=True).distinct().count()
        context['count_students_exits'] = students_different_exit_application
        context['orderby'] = orderby
        context["all_students"] = students
        
        context["finish_students_count"] = application.applicationstudent_set.all().filter(
            Q(
                Q(
                    Q(application__category=Application.MONITORIN_EXAM),
                    Q(start_time__isnull=False), 
                    Q(end_time__isnull=False)
                ) |
                Q(
                    Q(application__category=Application.PRESENTIAL),
                    Q(is_omr=True)
                ) |
                Q(
                    Q(application__category=Application.HOMEWORK),
                    Q(
                        Q(option_answers__isnull=False) |
                        Q(textual_answers__isnull=False) |
                        Q(file_answers__isnull=False)
                    )
                )
            ),
        ).distinct().count()

        context["missing_students_count"] = application.applicationstudent_set.all().filter(Q(
            Q(
                Q(application__category=Application.MONITORIN_EXAM),
                Q(start_time__isnull=True), 
                Q(end_time__isnull=True)
            ) |
            Q(
                Q(application__category=Application.PRESENTIAL),
                Q(is_omr=False)
            ) |
                Q(
                    Q(application__category=Application.HOMEWORK),
                    Q(
                        Q(option_answers__isnull=True),
                        Q(textual_answers__isnull=True),
                        Q(file_answers__isnull=True)
                    )
                )
        )).count()

        context["students"] = students.get_page(page)
        if q_student_name := self.request.GET.get('q_student_name', ''):
            context['q_student_name'] = q_student_name

        return context

class ApplicationExamStudentView(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'dashboard/applications/application_exam_student_detail.html'
    model = ApplicationStudent
    required_permissions = [settings.STUDENT, ]

    def dispatch(self, request, *args, **kwargs): 
        application_student = self.get_object()
        deny_student_stats_view = False
        if application_student.application.student_stats_permission_date:
            today = timezone.now().astimezone()
            deny_student_stats_view = application_student.application.student_stats_permission_date > today

        if application_student.application.is_happening or deny_student_stats_view:
            return HttpResponseForbidden()
            
        return super(ApplicationExamStudentView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ApplicationExamStudentView, self).get_context_data(**kwargs)
        
        questions = Question.objects.availables(self.get_object().application.exam).get_application_student_report(self.object).order_by(
            'examquestion__exam_teacher_subject__order', 'examquestion__order'
        )

        subjects = Subject.objects.filter(question__in=questions).distinct().annotate(
            total_questions=Count('question', filter=Q(question__in=questions), distinct=True)
        )

        application_student = ApplicationStudent.objects.filter(pk=self.object.pk)
        
        for subject in subjects:
            subject.data = application_student.get_annotation_count_answers_filter_subjects(
                subjects=[subject]
            ).values( 
                'total_answers',
                'total_correct_answers',
                'total_incorrect_answers',
                'total_partial_answers',
                'total_grade'
            ).first()

        context['questions'] = questions
        context['answers_count'] = questions.count()
        context['total_grade'] = questions.aggregate(total=Sum('teacher_grade')).get('total', 0.0)
        context['correct_answers_count'] = questions.filter(is_correct=True).count()
        context['incorrect_answers_count'] = questions.filter(is_incorrect=True).count()
        context['partial_answers_count'] = questions.filter(is_partial=True).count()
        context['knowledge_areas'] = KnowledgeArea.objects.student_application_general_report(self.object)
        context['subjects'] = subjects
        return context


class ApplicationExamStudentV2View(LoginRequiredMixin, CheckHasPermission, StudentCanViewResultsMixin, DetailView):
    template_name = 'dashboard/applications/v2/application_exam_student_detail.html'
    model = ApplicationStudent
    required_permissions = (settings.STUDENT, settings.TEACHER, settings.PARENT)

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated:
            if user.user_type == settings.PARENT:
                return redirect(reverse('external_result_application', kwargs={ "pk": self.get_object().id }))
            
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from fiscallizeon.exams.models import StatusQuestion

        application_student = self.object
        exam = application_student.application.exam

        show_ranking = exam.show_ranking

        rank_class = None
        count_class = None
        rank_unity = None
        count_unity = None
        rank_client = None
        count_client = None

        if show_ranking:
            rank_class, count_class = ApplicationStudent.get_rank(application_student, {
                'student__classes': application_student.get_last_class_student()
            })
            rank_unity, count_unity = ApplicationStudent.get_rank(application_student, {
                'student__classes__coordination__unity': application_student.get_last_class_student().coordination.unity
            })
            rank_client, count_client = ApplicationStudent.get_rank(application_student, {
                'student__client': application_student.student.client
            })

        if self.request.GET.get('open_question'):
            context['open_question'] = self.request.GET.get('open_question')


        this_exam_teacher_subjects = exam.examteachersubject_set
         
        # nomes das disciplinas para pré-visualização
        examteacher_subjects = this_exam_teacher_subjects.select_related('teacher_subject', 'teacher_subject__subject').order_by().distinct('teacher_subject__subject').values('teacher_subject__subject__name')

        # Remove a disciplinas estrangeira que não foi selecionada para a prova
        if examteacher_subjects.filter(is_foreign_language=True).exists():

            foreign_language_options = this_exam_teacher_subjects.filter(is_foreign_language=True).order_by('order')
            first_option = foreign_language_options.first()
            last_option = foreign_language_options.last() 

            if application_student.foreign_language == ApplicationStudent.ENGLISH:
                examteacher_subjects = examteacher_subjects.exclude(pk=last_option.pk)
            else:
                examteacher_subjects = examteacher_subjects.exclude(pk=first_option.pk)

        context['subjects_preview'] = examteacher_subjects

        # questões para pré-visualização
        questions = Question.objects.filter(exams__application__applicationstudent=application_student)
        questions_preview = questions.values('pk') # adicionar campos se necessário

        for question in questions_preview:
            # question_object = questions.get(pk=question['pk'])
            question['number_print'] = 0
            
        questions_preview = sorted(questions_preview, key=lambda x: x['number_print'])
        context['questions_preview'] = questions_preview

        is_enem_simulator = exam.is_enem_simulator
        
        
        context['performance'] = percentage_formatted(application_student.get_performance_v2())
        context['score'] = format_value(application_student.get_total_grade())
        context['is_enem_simulator'] = is_enem_simulator
        

        context['show_ranking'] = show_ranking

        context['rank_class'] = rank_class
        context['rank_unity'] = rank_unity
        context['rank_client'] = rank_client

        context['count_class'] = count_class
        context['count_unity'] = count_unity
        context['count_client'] = count_client        

        return context


class ApplicationExamStudentInsightView(LoginRequiredMixin, CheckHasPermission, StudentCanViewResultsMixin, DetailView):
    template_name = 'dashboard/applications/v2/application_exam_student_detail_insight.html'
    model = ApplicationStudent
    required_permissions = (settings.STUDENT, settings.TEACHER)

    def _get_performance(self, total, correct):
        if total <= 0:
            return 0

        return (correct / total) * 100

    def _get_result(self, queryset, field):
        result = []
        for obj in queryset:
            name = obj[field]
            if not name:
                name = 'Não definido'

            result.append(
                {
                    'name': name,
                    'count': obj['count'],
                    'performance': self._get_performance(
                        round_half_up(obj['weight'], 2), round_half_up(obj['score'], 2)
                    ),
                }
            )

        return result

    def get_topics(self, obj, application_student):
        option_correct = (
            OptionAnswer.objects.filter(
                question_option__question=OuterRef('question__pk'),
                student_application=application_student,
                status=OptionAnswer.ACTIVE,
            ).order_by('-created_at')
        )

        textual_correct = (
            TextualAnswer.objects.filter(
                question=OuterRef('question__pk'),
                student_application=application_student,
                teacher_grade=OuterRef('weight'),
            ).annotate(
                is_correct=Case(
                    When(teacher_grade=OuterRef('weight'), then=True),
                    default=False,
                )
            )
            .order_by('-created_at')
        )

        file_correct = (
            FileAnswer.objects.filter(
                question=OuterRef('question__pk'),
                student_application=application_student,
                teacher_grade=OuterRef('weight'),
            ).annotate(
                is_correct=Case(
                    When(teacher_grade=OuterRef('weight'), then=True),
                    default=False,
                )
            )
            .order_by('-created_at')
        )

        sum_answer_correct = (
            SumAnswer.objects.filter(
                question=OuterRef('question__pk'),
                student_application=application_student,
                grade=Value(1.0),
            ).annotate(
                is_correct=Case(
                    When(grade=Value(1.0), then=True),
                    default=False,
                )
            )
            .order_by('-created_at')
        )

        extra_filters = {'exam_teacher_subject__teacher_subject__subject': obj}
        if application_student.application.exam.is_abstract:
            extra_filters = {'question__subject': obj}

        exam_questions = (
            ExamQuestion.objects.filter(
                exam=application_student.application.exam,
                **extra_filters,
            )
            .annotate(
                is_correct=Subquery(
                    option_correct.values('question_option__is_correct')[:1]
                ),
                is_correct_textual=Subquery(
                    textual_correct.values('is_correct')[:1]
                ),
                is_correct_file=Subquery(
                    file_correct.values('is_correct')[:1]
                ),
                is_correct_sum_answer=Subquery(
                    sum_answer_correct.values('is_correct')[:1]
                ),
            )
            .values('question__topics__name')
            .annotate(
                count=Count('pk'),
                score=Coalesce(
                    Sum('weight', filter=Q(
                        Q(is_correct=True) | Q(is_correct_textual=True) | Q(is_correct_file=True) | Q(is_correct_sum_answer=True)
                    )), Decimal('0')
                ),
                weight=Sum('weight'),
            )
        )

        return self._get_result(exam_questions, 'question__topics__name')

    def get_abilities(self, obj, application_student):
        option_correct = (
            OptionAnswer.objects.filter(
                question_option__question=OuterRef('question__pk'),
                student_application=application_student,
                status=OptionAnswer.ACTIVE,
            ).order_by('-created_at')
        )

        textual_correct = (
            TextualAnswer.objects.filter(
                question=OuterRef('question__pk'),
                student_application=application_student,
                teacher_grade=OuterRef('weight'),
            ).annotate(
                is_correct=Case(
                    When(teacher_grade=OuterRef('weight'), then=True),
                    default=False,
                )
            )
            .order_by('-created_at')
        )

        file_correct = (
            FileAnswer.objects.filter(
                question=OuterRef('question__pk'),
                student_application=application_student,
                teacher_grade=OuterRef('weight'),
            ).annotate(
                is_correct=Case(
                    When(teacher_grade=OuterRef('weight'), then=True),
                    default=False,
                )
            )
            .order_by('-created_at')
        )

        sum_answer_correct = (
            SumAnswer.objects.filter(
                question=OuterRef('question__pk'),
                student_application=application_student,
                grade=Value(1.0),
            ).annotate(
                is_correct=Case(
                    When(grade=Value(1.0), then=True),
                    default=False,
                )
            )
            .order_by('-created_at')
        )

        extra_filters = {'exam_teacher_subject__teacher_subject__subject': obj}
        if application_student.application.exam.is_abstract:
            extra_filters = {'question__subject': obj}

        exam_questions = (
            ExamQuestion.objects.filter(
                exam=application_student.application.exam,
                **extra_filters,
            )
            .annotate(
                is_correct=Subquery(
                    option_correct.values('question_option__is_correct')[:1]
                ),
                is_correct_textual=Subquery(
                    textual_correct.values('is_correct')[:1]
                ),
                is_correct_file=Subquery(
                    file_correct.values('is_correct')[:1]
                ),
                is_correct_sum_answer=Subquery(
                    sum_answer_correct.values('is_correct')[:1]
                ),
            )
            .values('question__abilities__text')
            .annotate(
                count=Count('pk'),
                score=Coalesce(
                    Sum('weight', filter=Q(
                        Q(is_correct=True) | Q(is_correct_textual=True) | Q(is_correct_file=True) | Q(is_correct_sum_answer=True)
                    )), Decimal('0')
                ),
                weight=Sum('weight'),
            )
        )

        return self._get_result(exam_questions, 'question__abilities__text')

    def get_competences(self, obj, application_student):
        option_correct = (
            OptionAnswer.objects.filter(
                question_option__question=OuterRef('question__pk'),
                student_application=application_student,
                status=OptionAnswer.ACTIVE,
            ).order_by('-created_at')
        )

        textual_correct = (
            TextualAnswer.objects.filter(
                question=OuterRef('question__pk'),
                student_application=application_student,
                teacher_grade=OuterRef('weight'),
            ).annotate(
                is_correct=Case(
                    When(teacher_grade=OuterRef('weight'), then=True),
                    default=False,
                )
            )
            .order_by('-created_at')
        )

        file_correct = (
            FileAnswer.objects.filter(
                question=OuterRef('question__pk'),
                student_application=application_student,
                teacher_grade=OuterRef('weight'),
            ).annotate(
                is_correct=Case(
                    When(teacher_grade=OuterRef('weight'), then=True),
                    default=False,
                )
            )
            .order_by('-created_at')
        )

        sum_answer_correct = (
            FileAnswer.objects.filter(
                question=OuterRef('question__pk'),
                student_application=application_student,
                grade=Value(1.0),
            ).annotate(
                is_correct=Case(
                    When(grade=Value(1.0), then=True),
                    default=False,
                )
            )
            .order_by('-created_at')
        )

        extra_filters = {'exam_teacher_subject__teacher_subject__subject': obj}
        if application_student.application.exam.is_abstract:
            extra_filters = {'question__subject': obj}

        exam_questions = (
            ExamQuestion.objects.filter(
                exam=application_student.application.exam,
                **extra_filters,
            )
            .annotate(
                is_correct=Subquery(
                    option_correct.values('question_option__is_correct')[:1]
                ),
                is_correct_textual=Subquery(
                    textual_correct.values('is_correct')[:1]
                ),
                is_correct_file=Subquery(
                    file_correct.values('is_correct')[:1]
                ),
                is_correct_sum_answer=Subquery(
                    sum_answer_correct.values('is_correct')[:1]
                ),
            )
            .values('question__competences__text')
            .annotate(
                count=Count('pk'),
                score=Coalesce(
                    Sum('weight', filter=Q(
                        Q(is_correct=True) | Q(is_correct_textual=True) | Q(is_correct_file=True) | Q(is_correct_sum_answer=True)
                    )), Decimal('0')
                ),
                weight=Sum('weight'),
            )
        )

        return self._get_result(exam_questions, 'question__competences__text')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        application_student = self.get_object()

        option_correct = (
            OptionAnswer.objects.filter(
                question_option__question=OuterRef('question__pk'),
                student_application=application_student,
                status=OptionAnswer.ACTIVE,
            ).order_by('-created_at')
        )

        textual_correct = (
            TextualAnswer.objects.filter(
                question=OuterRef('question__pk'),
                student_application=application_student,
                teacher_grade=OuterRef('weight'),
            ).annotate(
                is_correct=Case(
                    When(teacher_grade=OuterRef('weight'), then=True),
                    default=False,
                )
            )
            .order_by('-created_at')
        )

        file_correct = (
            FileAnswer.objects.filter(
                question=OuterRef('question__pk'),
                student_application=application_student,
                teacher_grade=OuterRef('weight'),
            ).annotate(
                is_correct=Case(
                    When(teacher_grade=OuterRef('weight'), then=True),
                    default=False,
                )
            )
            .order_by('-created_at')
        )

        sum_answer_correct = (
            SumAnswer.objects.filter(
                question=OuterRef('question__pk'),
                student_application=application_student,
                grade=Value(1.0),
            ).annotate(
                is_correct=Case(
                    When(grade=Value(1.0), then=True),
                    default=False,
                )
            )
            .order_by('-created_at')
        )
       
        queryset_topics = application_student.get_exam_questions_all().annotate(
            is_correct=Subquery(
                option_correct.values('question_option__is_correct')[:1]
            ),
            is_correct_textual=Subquery(
                textual_correct.values('is_correct')[:1]
            ),
            is_correct_file=Subquery(
                file_correct.values('is_correct')[:1]
            ),
            is_correct_sum_answer=Subquery(
                sum_answer_correct.values('is_correct')[:1]
            ),
        ).values(
            'question__topics__pk',
            'question__topics__name',
            'question__subject__name',
        ).annotate(
            count=Count('pk'),
            count_is_correct=Count('pk', filter=Q(
                Q(is_correct=True) | Q(is_correct_textual=True) | Q(is_correct_file=True) | Q(is_correct_sum_answer=True)
            )),
            total_weight=Sum('weight'),
            score=Coalesce(
                Sum('weight', filter=Q(
                    Q(is_correct=True) | Q(is_correct_textual=True) | Q(is_correct_file=True) | Q(is_correct_sum_answer=True)
                )), Decimal('0')
            ),
        ).annotate(
            diff=F('total_weight') - F('score'),
        ).filter(question__topics__name__isnull=False, diff__gt=0).order_by('-diff')

        queryset_abilities = application_student.get_exam_questions_all().annotate(
            is_correct=Subquery(
                option_correct.values('question_option__is_correct')[:1]
            ),
            is_correct_textual=Subquery(
                textual_correct.values('is_correct')[:1]
            ),
            is_correct_file=Subquery(
                file_correct.values('is_correct')[:1]
            ),
            is_correct_sum_answer=Subquery(
                sum_answer_correct.values('is_correct')[:1]
            ),
        ).values(
            'question__abilities__pk',
            'question__abilities__text',
        ).annotate(
            count=Count('pk', distinct=True),
            count_is_correct=Count('pk', filter=Q(
                Q(is_correct=True) | Q(is_correct_textual=True) | Q(is_correct_file=True) | Q(is_correct_sum_answer=True)
            ), distinct=True),
            total_weight=Sum('weight'),
            score=Coalesce(
                Sum('weight', filter=Q(
                    Q(is_correct=True) | Q(is_correct_textual=True) | Q(is_correct_file=True) | Q(is_correct_sum_answer=True)
                )), Decimal('0')
            ),
        ).annotate(
            diff=F('total_weight') - F('score'),
        ).filter(question__abilities__text__isnull=False, diff__gt=0).order_by('-diff')

        queryset_competences = application_student.get_exam_questions_all().annotate(
            is_correct=Subquery(
                option_correct.values('question_option__is_correct')[:1]
            ),
            is_correct_textual=Subquery(
                textual_correct.values('is_correct')[:1]
            ),
            is_correct_file=Subquery(
                file_correct.values('is_correct')[:1]
            ),
            is_correct_sum_answer=Subquery(
                sum_answer_correct.values('is_correct')[:1]
            ),
        ).values(
            'question__competences__pk',
            'question__competences__text',
        ).annotate(
            count=Count('pk', distinct=True),
            count_is_correct=Count('pk', filter=Q(
                Q(is_correct=True) | Q(is_correct_textual=True) | Q(is_correct_file=True) | Q(is_correct_sum_answer=True)
            ), distinct=True),
            total_weight=Sum('weight'),
            score=Coalesce(
                Sum('weight', filter=Q(
                    Q(is_correct=True) | Q(is_correct_textual=True) | Q(is_correct_file=True) | Q(is_correct_sum_answer=True)
                )), Decimal('0')
            ),
        ).annotate(
            diff=F('total_weight') - F('score'),
        ).filter(question__competences__text__isnull=False, diff__gt=0).order_by('-diff')

        insight_topics = []
        for ta in queryset_topics:
            performance = (
                (
                    (
                        round_half_up(ta['score'], 2)
                        / round_half_up(ta['total_weight'], 2)
                    )
                    * 100
                )
                if ta['total_weight'] > 0
                else 0
            )
            insight_topics.append({
                'id': ta['question__topics__pk'],
                'name': ta['question__topics__name'],
                'diff': ta['diff'],
                'score': ta['score'],
                'subject': ta['question__subject__name'],
                'total_weight': ta['total_weight'],
                'performance': percentage_formatted(performance),
                'count': ta['count'],
                'count_incorrect':ta['count'] - ta['count_is_correct']
            })

        insight_commons = []
        for tb in queryset_abilities:
            performance = (
                (
                    (
                        round_half_up(tb['score'], 2)
                        / round_half_up(tb['total_weight'], 2)
                    )
                    * 100
                )
                if tb['total_weight'] > 0
                else 0
            )
            insight_commons.append({
                'id': tb['question__abilities__pk'],
                'name': " ".join(tb['question__abilities__text'].split()),
                'diff': tb['diff'],
                'score': tb['score'],
                'total_weight': tb['total_weight'],
                'performance': percentage_formatted(performance),
                'performance_progress': int(round_half_up(performance, 2)),
                'kind': 0,
                'kind_display': 'Habilidade',
                'count': tb['count'],
                'count_incorrect':tb['count'] - tb['count_is_correct']
            })

        for tc in queryset_competences:
            performance = (
                (
                    (
                        round_half_up(tc['score'], 2)
                        / round_half_up(tc['total_weight'], 2)
                    )
                    * 100
                )
                if tc['total_weight'] > 0
                else 0
            )
            insight_commons.append({
                'id': tc['question__competences__pk'],
                'name': " ".join(tc['question__competences__text'].split()),
                'diff': tc['diff'],
                'score': tc['score'],
                'total_weight': tc['total_weight'],
                'performance': percentage_formatted(performance),
                'performance_progress': int(round_half_up(performance, 2)),
                'kind': 1,
                'kind_display': 'Competência',
                'count': tc['count'],
                'count_incorrect':tc['count'] - tc['count_is_correct']
            })

        exam_questions = application_student.get_exam_questions(exclude_annuleds=True)

        keys = {
            'id': 'exam_teacher_subject__teacher_subject__subject__id',
            'name': 'exam_teacher_subject__teacher_subject__subject__name',
            'knowledge_area': 'exam_teacher_subject__teacher_subject__subject__knowledge_area__name',
        }
        if application_student.application.exam.is_abstract:
            keys = {
                'id': 'question__subject__id',
                'name': 'question__subject__name',
                'knowledge_area': 'question__subject__knowledge_area__name',
            }

        list_data = []
        
        for examquestion in exam_questions:
            performance = 0
            if examquestion['weight__sum'] > 0:
                performance = (
                    (
                        round_half_up(examquestion['score'], 2) / round_half_up(examquestion['weight__sum'], 2)
                    ) * 100
                )

            list_level = [
                {
                    'key': 'easy',
                    'name': 'fáceis',
                    'total': examquestion["easy_count"],
                    'correct': examquestion["correct_easy_count"],
                    'diff': examquestion["easy_count"] - examquestion["correct_easy_count"],
                    'performance': int(round_half_up((examquestion["correct_easy_count"] / examquestion["easy_count"] * 100), 2)) if examquestion["easy_count"] > 0 else 0,
                },
                {
                    'key': 'medium',
                    'name': 'médias',
                    'total': examquestion["medium_count"],
                    'correct': examquestion["correct_medium_count"],
                    'diff': examquestion["medium_count"] - examquestion["correct_medium_count"],
                    'performance': int(round_half_up((examquestion["correct_medium_count"] / examquestion["medium_count"] * 100), 2)) if examquestion["medium_count"] > 0 else 0,
                },
                {
                    'key': 'hard',
                    'name': 'difíceis',
                    'total': examquestion["hard_count"],
                    'correct': examquestion["correct_hard_count"],
                    'diff': examquestion["hard_count"] - examquestion["correct_hard_count"],
                    'performance': int(round_half_up((examquestion["correct_hard_count"] / examquestion["hard_count"] * 100), 2)) if examquestion["hard_count"] > 0 else 0,
                },
                {
                    'key': 'undefined',
                    'name': 'de nível não definido',
                    'total': examquestion["undefined_count"],
                    'correct': examquestion["correct_undefined_count"],
                    'diff': examquestion["undefined_count"] - examquestion["correct_undefined_count"],
                    'performance': int(round_half_up((examquestion["correct_undefined_count"] / examquestion["undefined_count"] * 100), 2)) if examquestion["undefined_count"] > 0 else 0,
                }
            ]

            max_diff_level = max(list_level, key=lambda x:x['diff'])

            if (examquestion["weight__sum"] - examquestion["score"]) > 0:
                list_data.append({
                    'id': examquestion[keys['id']],
                    'name': examquestion[keys['name']],
                    'knowledge_area': examquestion[keys['knowledge_area']],
                    'quantity': examquestion['pk__count'],
                    'correct_count': examquestion['answer_correct__count'],
                    'partial_count': examquestion['answer_partial__count'],
                    'incorrect_count': examquestion['answer_incorrect__count'],
                    'score': format_value(examquestion['score']),
                    'total_weight': format_value(examquestion['weight__sum']),
                    'performance': format_value(performance),
                    'performance_formatted': percentage_formatted(performance),
                    'performance_diff': format_value(100 - performance),
                    'diff': examquestion["weight__sum"] - examquestion["score"],
                    'max_diff_level': max_diff_level,
                    'total_open_questions': examquestion['pk__count']-examquestion['answer_correct__count']
                })

        subjects = sorted(list_data, key=lambda x: x['diff'], reverse=True)

        it = sorted(insight_topics, key=lambda x: x['diff'], reverse=True)
        ic = sorted(insight_commons, key=lambda x: x['diff'], reverse=True)

        questions_oportunity = application_student.check_question_perf()
        questions_easy = [{'object': exameasy, 'performance_total': 0, 'kind': 'level'} for exameasy in application_student.get_exam_questions_easy_all()]

        context['subjects'] = subjects
        context['topics'] = it
        context['commons'] = ic
        context['questions'] = questions_oportunity + questions_easy

        retry_answers = RetryAnswer.objects.filter(
            application_student=application_student
        )

        context['retry_answers'] = []

        for retry_answer in retry_answers:
            context['retry_answers'].append(
                {
                    'question_pk': str(retry_answer.exam_question.question.pk),
                    'exam_question_pk': str(retry_answer.exam_question.pk),
                    'subject': str(retry_answer.exam_question.exam_teacher_subject.teacher_subject.subject.pk) if not application_student.application.exam.is_abstract else str(retry_answer.exam_question.question.subject.pk) if retry_answer.exam_question.question.subject else '',
                    'abilities':[str(abilitie.pk) for abilitie in retry_answer.exam_question.question.abilities.all()],
                    'competences':[str(competences.pk) for competences in retry_answer.exam_question.question.competences.all()],
                    'topics':[str(topic.pk) for topic in retry_answer.exam_question.question.topics.all()]
                }
            )

        return context


class ApplicationPreviousFeedbackView(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'dashboard/applications/application_previous_feedback.html'
    model = ApplicationStudent
    required_permissions = [settings.STUDENT, ]

    def dispatch(self, request, *args, **kwargs):
        if not self.request.user.is_authenticated or self.request.user.is_anonymous:
            return redirect("accounts:login")

        if  not self.request.user.client_show_previews_template_student:
            messages.warning(request, "Sua instituição não tem acesso a este serviço.")
            return redirect("core:redirect_dashboard")
        application_student = self.get_object()

        if application_student.application.has_open_applications_exam or not application_student.application.is_time_finished:
            return HttpResponseForbidden()
            
        return super(ApplicationPreviousFeedbackView, self).dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super(ApplicationPreviousFeedbackView, self).get_context_data(**kwargs)
        
        questions = self.get_object().application.exam.questions.availables(
            self.get_object().application.exam
        ).filter(
            number_is_hidden=False
        ).get_application_student_report(
            self.get_object()
        ).distinct()

        # questions = Question.objects.availables(
        #     self.get_object().application.exam
        # ).get_application_student_report(
        #     self.object
        # ).order_by(
        #     'examquestion__exam_teacher_subject__order', 
        #     'examquestion__order',
        # )   

        questions_counts = questions.aggregate(			
			textual=Count('category', filter=Q(category=Question.TEXTUAL)),
			choice=Count('category', filter=Q(category=Question.CHOICE)),
			file=Count('category', filter=Q(category=Question.FILE)),
			sum_question=Count('category', filter=Q(category=Question.SUM_QUESTION)),
		)
        
        context['questions_counts'] = questions_counts
        context['questions'] = questions.order_by(
            'examquestion__exam_teacher_subject__order', 'examquestion__order'
        )
        context['answers_count'] = questions.count()        
        context['knowledge_areas'] = KnowledgeArea.objects.student_application_general_report(self.object)
        return context

class ApplicationAddAndDelStudent(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    template_name = 'dashboard/applications/application_add_del_students.html'
    model = Application
    form_class = ApplicationEditStudentsForm
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    permission_required = 'applications.can_add_and_remove_students'
    success_message = 'Aplicação atualizada com sucesso'

    def dispatch(self, request, *args, **kwargs):
        application = self.get_object()
        user = self.request.user

        if application.exam.not_applicable:
            messages.warning(self.request, 'O caderno dessa aplicação está marcado como não aplicável.')
            return redirect(f'{reverse("applications:applications_list")}?{self.request.META.get("QUERY_STRING", None)}')

        if not user.is_authenticated or user.user_type == settings.TEACHER and (not application.exam.created_by == user or not user.client_teachers_can_elaborate_exam):
            messages.error(self.request, 'Você não tem permissão para adicionar aluno a esta aplicação')
            return redirect(reverse('core:redirect_dashboard'))

        return super().dispatch(request, *args, **kwargs)
    
    
    def get_queryset(self):
        queryset = super(ApplicationAddAndDelStudent, self).get_queryset()
        queryset = queryset.annotate(duration = ExpressionWrapper(F('end') - F('start'), output_field=fields.DurationField()))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def get_success_url(self):
        return f'{reverse("applications:applications_list")}?{self.request.META.get("QUERY_STRING", None)}'


class ExternalResultApplication(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'dashboard/applications/v2/application_exam_student_detail.html'
    required_permissions = [settings.PARENT]
    model = ApplicationStudent
    
    def dispatch(self, request, *args, **kwargs):
        application_student = self.get_object()
        user = request.user
        
        if user.is_authenticated:
        
            if user.user_type == 'parent' and (not application_student.student in user.parent.students.all()):
                return HttpResponseForbidden()
            
            deny_student_stats_view = False

            if not application_student.application.student_stats_permission_date and not application_student.application.release_result_at_end:
                return HttpResponseForbidden()
            
            if application_student.application.student_stats_permission_date:
                today = timezone.now().astimezone()
                deny_student_stats_view = (
                    application_student.application.student_stats_permission_date > today
                )

            if application_student.application.is_happening or deny_student_stats_view:
                return HttpResponseForbidden()
        
        
        return super().dispatch(request, *args, **kwargs)

    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from fiscallizeon.exams.models import StatusQuestion
    
        application_student = self.get_object()
        
        show_ranking = application_student.application.exam.show_ranking

        rank_class = None
        count_class = None
        rank_unity = None
        count_unity = None
        rank_client = None
        count_client = None

        if show_ranking:
            rank_class, count_class = ApplicationStudent.get_rank(application_student, {
                'student__classes': application_student.get_last_class_student()
            })
            rank_unity, count_unity = ApplicationStudent.get_rank(application_student, {
                'student__classes__coordination__unity': application_student.get_last_class_student().coordination.unity
            })
            rank_client, count_client = ApplicationStudent.get_rank(application_student, {
                'student__client': application_student.student.client
            })
    
        if self.request.GET.get('open_question'):
            context['open_question'] = self.request.GET.get('open_question')

        questions = (
            Question.objects.availables(application_student.application.exam)
            .get_application_student_report(application_student)
            .order_by(
                'examquestion__exam_teacher_subject__order', 'examquestion__order'
            ).annotate(
                last_status=Subquery(
                    StatusQuestion.objects.filter(
                        active=True, 
                        exam_question__question=OuterRef('pk'), 
                        exam_question__exam=application_student.application.exam
                    ).order_by('-created_at').values('status')[:1]),
                give_score=Subquery(
                    StatusQuestion.objects.filter(
                        active=True,
                        exam_question__question=OuterRef('pk'),
                        exam_question__exam=application_student.application.exam,
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
        
        examteacher_subjects = application_student.application.exam.examteachersubject_set.all()

        questions_count = questions.count()
        questions_without_annuleds = questions.availables(application_student.application.exam, exclude_annuleds=True)
        correct_count = questions_without_annuleds.filter(is_correct=True).distinct().count()

        context['questions_count'] = questions_count
        context['correct_count'] = correct_count
        context['partial_count'] = questions_without_annuleds.filter(is_partial=True).count()
        context['incorrect_count'] = questions_without_annuleds.filter(is_incorrect=True).count()

        context['performance'] = percentage_formatted(
            application_student.get_performance(recalculate=True)
        )
        context['score'] = format_value(application_student.get_score())
        
        context['examteacher_subjects'] = [
            {
                "subject": exam_teacher_subject.teacher_subject.subject,
                "examquestions": ExamQuestion.objects.filter(
                    exam=exam_teacher_subject.exam,
                    exam_teacher_subject__teacher_subject__subject=exam_teacher_subject.teacher_subject.subject
                ).distinct().availables(),
                "correct_count": application_student.get_total_correct_answers(exam_teacher_subject.teacher_subject.subject),
                "incorrect_count": application_student.get_total_incorrect_answers(exam_teacher_subject.teacher_subject.subject),
                "partial_count": application_student.get_total_correct_partial_answers(exam_teacher_subject.teacher_subject.subject),
                "score": application_student.get_score(subject=exam_teacher_subject.teacher_subject.subject),
                "performance": application_student.get_performance(subject=exam_teacher_subject.teacher_subject.subject, recalculate=True),
                "total_weight": application_student.get_total_weight(subject=exam_teacher_subject.teacher_subject.subject),
            } for exam_teacher_subject in examteacher_subjects.order_by().distinct('teacher_subject__subject')
        ]

        questions_count = questions.count()
        correct_count = questions.filter(is_correct=True).count()

        context['questions_count'] = questions_count
        context['correct_count'] = correct_count
        context['partial_count'] = questions.filter(is_partial=True).count()
        context['incorrect_count'] = questions.filter(is_incorrect=True).count()

        context['questions'] = questions

        context['show_ranking'] = show_ranking

        context['rank_class'] = rank_class
        context['rank_unity'] = rank_unity
        context['rank_client'] = rank_client

        context['count_class'] = count_class
        context['count_unity'] = count_unity
        context['count_client'] = count_client
        
        context['is_popup'] = 1
        
        context['is_external'] = 1

        return context
    
class PrintApplicationsListView(LoginRequiredMixin, CheckHasPermission, ListView):
    template_name = 'dashboard/applications/print_applications_list.html'
    required_permissions = [settings.COORDINATION, settings.PARTNER]
    # permission_required = 'applications.can_access_print_list'
    paginate_by = 20
    model = Application

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if user.is_authenticated and not (user.user_type == 'partner' or user.user_type == 'coordination'):
            return HttpResponseForbidden()

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        today = timezone.localtime(timezone.now())
        user = self.request.user
        queryset = Application.objects.filter(print_ready=True, category=Application.PRESENTIAL, exam__coordinations__unity__client__in=user.get_clients_cache()).order_by('-created_at').distinct()
        
        if self.request.GET.get('year'):
            queryset = queryset.filter(
                date__year=self.request.GET.get('year'),
            )
        else:
            queryset = queryset.filter(
                date__year=today.year,
            )

        if self.request.GET.get('q_name', ""):
            
            query_terms = [Q(exam__name__unaccent__icontains=term) for term in self.request.GET.get('q_name').split(' ')]
            query = Q()
            
            for quey in query_terms:
                query &= quey

            queryset = queryset.filter(
                query
            )

        if self.request.GET.get('q_unities', ""):
            queryset = queryset.filter(
                exam__coordinations__unity__in=self.request.GET.getlist('q_unities', "")
            )

        if self.request.GET.get('q_is_printed', ""):
            queryset = queryset.filter(
                exam__is_printed=True
            )
        if self.request.GET.get('q_book_is_printed', ""):
            queryset = queryset.filter(
                book_is_printed=True
            )
        if self.request.GET.getlist('q_grades', ""):
            queryset = queryset.filter(
                exam__teacher_subjects__subject__knowledge_area__grades__pk__in=self.request.GET.getlist('q_grades', "")
            )
        if self.request.GET.getlist('q_systems', ""):
            queryset = queryset.filter(
                exam__education_system__in=self.request.GET.getlist('q_systems', "")
                )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        context['q_name'] = self.request.GET.get('q_name', "")
        context['q_grades'] = self.request.GET.get('q_grades', "")
        context['q_unities'] = self.request.GET.get('q_unities', "")
        context['q_is_printed'] = self.request.GET.get('q_is_printed', "")
        context['q_book_is_printed'] = self.request.GET.get('q_book_is_printed', "")
        context['q_systems'] = self.request.GET.get('q_systems', "")

        list_filters = [context['q_name'], context["q_grades"], context["q_unities"], context['q_is_printed'], context['q_book_is_printed'], context['q_systems']]

        context['count_filters'] = len(list_filters) - list_filters.count("")
        filter_condition = Q()
        if user.has_high_school_coordinations:
            filter_condition |= Q(level=Grade.HIGHT_SCHOOL)

        if user.has_elementary_school_only_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL)

        if user.has_elementary_school2_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL_2)

        context["grades"] = Grade.objects.filter(filter_condition)
        context["unities"] = Unity.objects.filter(client__in=user.get_clients_cache())
        context["systems"] = EducationSystem.objects.filter(client__in=user.get_clients_cache())

        params_string = self.request.get_full_path().split('?')
        context["export_list_url"] = reverse('applications:application_export_print_list') + "?"
        if len(params_string) > 1:
            context["export_list_url"] += f"{params_string[1]}"

        return context

class TypeApplicationListView(LoginRequiredMixin, CheckHasPermission, ListView):
    template_name = 'dashboard/applications/type_application_list.html'
    required_permissions = [settings.COORDINATION]
    model = ApplicationType
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if user.is_authenticated and not user.client_has_customize_application:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('applications:applications_list'))

        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        
        queryset = super(TypeApplicationListView, self).get_queryset()
        queryset = queryset.filter(
            client__in=self.request.user.get_clients_cache()
        ).order_by('name')
        
        return queryset
    
class TypeApplicationCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    template_name = 'dashboard/applications/type_application_create_update.html'
    required_permissions = [settings.COORDINATION]
    model = ApplicationType
    fields = ['name']

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if user.is_authenticated and not user.client_has_customize_application:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('applications:applications_list'))

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.client = self.request.user.client 
        return super().form_valid(form)
    
class TypeApplicationUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):    
    template_name = 'dashboard/applications/type_application_create_update.html'
    required_permissions = [settings.COORDINATION]
    model = ApplicationType
    fields = ['name']

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if user.is_authenticated and not user.client_has_customize_application:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('applications:applications_list'))

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        form.instance.client = self.request.user.client 
        return super().form_valid(form)
    
class TypeApplicationDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = ApplicationType
    required_permissions = [settings.COORDINATION]
    success_message = "Tipo de aplicação removida com sucesso!"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(TypeApplicationDeleteView, self).delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('applications:type_application_list')
    
class ApplicationsExportPdf(LoginRequiredMixin, CheckHasPermission, ListView):
    template_name = 'dashboard/applications/applications_export_pdf.html'
    required_permissions = [settings.COORDINATION, settings.PARTNER]
    model = Application

    def get_queryset(self):
        today = timezone.localtime(timezone.now())
        user = self.request.user
        queryset = Application.objects.filter(print_ready=True, category=Application.PRESENTIAL, exam__coordinations__unity__client__in=user.get_clients_cache()).order_by('-created_at').distinct()
        
        if self.request.GET.get('year'):
            queryset = queryset.filter(
                date__year=self.request.GET.get('year'),
            )
        else:
            queryset = queryset.filter(
                date__year=today.year,
            )

        if self.request.GET.get('q_name', ""):
            queryset = queryset.filter(
                exam__name__unaccent__icontains=self.request.GET.get('q_name', "")
            )

        if self.request.GET.get('q_unities', ""):
            queryset = queryset.filter(
                exam__coordinations__unity__in=self.request.GET.getlist('q_unities', "")
            )

        if self.request.GET.get('q_is_printed', ""):
            queryset = queryset.filter(
                exam__is_printed=True
            )
        if self.request.GET.get('q_book_is_printed', ""):
            queryset = queryset.filter(
                book_is_printed=True
            )
        if self.request.GET.getlist('q_grades', ""):
            queryset = queryset.filter(
                exam__teacher_subjects__subject__knowledge_area__grades__pk__in=self.request.GET.getlist('q_grades', "")
                )
        if self.request.GET.getlist('q_systems', ""):
            queryset = queryset.filter(
                exam__education_system__in=self.request.GET.getlist('q_systems', "")
                )
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["classes_context"] = SchoolClass.objects.filter(applications__in=self.get_queryset(), students__user__is_active=True).annotate(students_count=Count('students')).filter(students_count__gt=0).order_by('coordination__unity__name')
        return context
    
class ApplicationStudentsImportView(LoginRequiredMixin, CheckHasPermission, FormView):
    template_name = 'dashboard/applications/imports/application_students_import.html'
    model = ApplicationStudent
    form_class = ApplicationStudentImportForm
    success_url = reverse_lazy('applications:application_students_import')
    permission_required = 'students.can_import_students_application'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['units'] = Unity.objects.filter(client__in=self.request.user.get_clients_cache())
        return context

    def form_valid(self, form):
        import os
        from fiscallizeon.applications.tasks.application_students_import import application_students_import
        from django.core.files.storage import FileSystemStorage
        from fiscallizeon.core.storage_backends import PrivateMediaStorage
        
        file = form.cleaned_data.get('file')

        os.makedirs('tmp/csv_import', exist_ok=True)

        tmp_file = os.path.join('tmp/csv_import', file.name)
        FileSystemStorage(location="tmp/csv_import").save(file.name, file)

        fs = PrivateMediaStorage()
        saved_file = fs.save(
            f'temp/{file.name}',
            open(tmp_file, 'rb')
        )
        os.remove(tmp_file)
        csv_file_url = fs.url(saved_file)
            
        task_id = f'IMPORT_APPLICATION_STUDENTS_{str(self.request.user.id)}'
        application_students_import.apply_async(task_id=task_id,
            kwargs={
                'user_id': self.request.user.id,
                'csv_file_url': csv_file_url,
            }
        ).forget()
            
        return super().form_valid(form)



class ApplicationEssayDetailView(LoginRequiredMixin, CheckHasPermission, StudentCanViewResultsMixin, DetailView):
    template_name = 'dashboard/applications/application_student_essay_detail.html'
    model = ApplicationStudent
    required_permissions = (settings.STUDENT, settings.TEACHER, settings.PARENT)

    def dispatch(self, request, *args, **kwargs):
        
        user = request.user
        
        if user.is_authenticated:
            
            if not user.client_has_essay_system:
                messages.warning(request, 'Cliente não possui este módulo')
                return redirect('core:redirect_dashboard')
        
            if user.user_type == settings.PARENT:
                return redirect(reverse('external_result_application', kwargs={ "pk": self.get_object().id }))
            
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        return context    

application_student_list = ApplicationStudentListView.as_view()
application_student_detail = ApplicationStudentDetailView.as_view()
application_exam_student_detail = ApplicationExamStudentView.as_view()
application_exam_student_detail_v2 = ApplicationExamStudentV2View.as_view()
application_exam_student_detail_insight = ApplicationExamStudentInsightView.as_view()
application_previous_feedback = ApplicationPreviousFeedbackView.as_view()

applications_list = ApplicationListView.as_view()
applications_create = ApplicationCreateView.as_view()
applications_create_multiple = ApplicationCreateMultipleView.as_view()
applications_update = ApplicationUpdateView.as_view()
applications_delete = ApplicationDeleteView.as_view()
applications_disclose = ApplicationDiscloseUpdateView.as_view()
applications_detail = ApplicationDetailView.as_view()

applications_monitoring = ApplicationMonitoringListView.as_view()

applications_add_del_student = ApplicationAddAndDelStudent.as_view()

applications_monitoring_inspector = ApplicationMonitoringInspectorView.as_view()
applications_monitoring_student = ApplicationMonitoringStudentView.as_view()
applications_orientations_student = ApplicationOrientationsStudentView.as_view()

applications_homework_student = ApplicationHomeWorkStudentView.as_view()

external_result_application = ExternalResultApplication.as_view()

print_applications_list = PrintApplicationsListView.as_view()
type_application_list = TypeApplicationListView.as_view()
type_application_create = TypeApplicationCreateView.as_view()
type_application_update = TypeApplicationUpdateView.as_view()
type_application_delete = TypeApplicationDeleteView.as_view()
applications_export_pdf = ApplicationsExportPdf.as_view()

application_students_import = ApplicationStudentsImportView.as_view()
clear_all_answers_and_redirect =  ClearAllAnswersAndRedirectView.as_view()