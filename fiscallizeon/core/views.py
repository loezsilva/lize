import random
import os
import requests

from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone
from django.db.models import (
    Q, F, ExpressionWrapper, fields, DateTimeField, Case, When, Value, BooleanField, Sum, Subquery, OuterRef, Exists, Count
)
from django.db.models.functions import Length
from django.core.files.base import ContentFile
from django.views.generic import View
from django.core.cache import cache
from django.apps import apps

from django.shortcuts import redirect, render, get_object_or_404, resolve_url as r
from django.urls import reverse
from fiscallizeon.questions.models import Question
from rest_framework.views import APIView
from django.views.generic.base import TemplateView
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth import login
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from fiscallizeon.accounts.views import (
    set_cookie_authorization, get_lastest_refresh_token, refresh_token,
)
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.students.models import Student
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.exams.models import Exam, ExamQuestion, ExamTeacherSubject, StatusQuestion
from fiscallizeon.subjects.models import Subject, Grade
from fiscallizeon.core.models import Config
from django.http import Http404, HttpResponse

from fiscallizeon.clients.models import Client, SchoolCoordination, Unity, TeachingStage
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.students.models import Student

from fiscallizeon.exams.mixins import ExamTeacherSubjectMixin
from fiscallizeon.analytics.models import GenericPerformancesFollowUp

from django.contrib.auth.mixins import UserPassesTestMixin
from hijack.views import AcquireUserView


class PrimaryReplicaRouter:
    def db_for_read(self, model, **hints):
        return random.choice(settings.DATABASE_ROUTER_READ_LIST)

    def db_for_write(self, model, **hints):
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        db_set = {x for x in set(settings.DATABASE_ROUTER_READ_LIST)}
        if obj1._state.db in db_set and obj2._state.db in db_set:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return True

class AuthDbRouter:
    route_app_labels = {'auth', 'contenttypes', 'accounts', 'sessions'}

    def db_for_read(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'default'
        return None

    def db_for_write(self, model, **hints):
        if model._meta.app_label in self.route_app_labels:
            return 'default'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        if (
            obj1._meta.app_label in self.route_app_labels or
            obj2._meta.app_label in self.route_app_labels
        ):
           return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if app_label in self.route_app_labels:
            return db == 'default'
        return None


class Healthcheck(TemplateView):
    template_name = 'status.html'

class TermsView(TemplateView):
    template_name = 'terms_template.html'

    def get_context_data(self, **kwargs):
        context = super(TermsView, self).get_context_data(**kwargs)

        slug = kwargs.get("slug")

        if slug == "aviso-privacidade":
            context["content"] = Config.objects.all().first().privacy
        elif slug == "condicoes-uso":
            context["content"] = Config.objects.all().first().terms_of_use
        elif slug == "condicoes-uso-fiscais":
            context["content"] = Config.objects.all().first().terms_of_use_inspectors
        else:
            raise Http404("Página não existe")

        return context


@login_required
def redirect_dashboard(request, reason=""):
    if request.user.client_has_allow_login_only_google and request.user.must_change_password:
        request.user.must_change_password = False
        request.user.save()

    if request.user.user_type == settings.COORDINATION:
        if request.user.must_change_password:
            request.session['must_change_password'] = True
            return redirect('accounts:password_change')

        if request.user.onboarding_responsible and not request.user.client_uncached.already_full_onboarded:
            return redirect('onboarding:index')

        return redirect("core:dashboard_coordination")
    elif request.user.is_freemium:
        if request.user.must_change_password:
            request.session['must_change_password'] = True
            return redirect('accounts:password_change')
        return redirect("core:dashboard_freemium")
    elif request.user.user_type == settings.INSPECTOR:
        if request.user.must_change_password:
            request.session['must_change_password'] = True
            return redirect('accounts:password_change')
        return redirect("core:dashboard_inspector")
    elif request.user.user_type == settings.TEACHER:
        if request.user.must_change_password:
            request.session['must_change_password'] = True
            return redirect('accounts:password_change')
        return redirect("core:dashboard_teacher") 
    elif request.user.user_type == settings.STUDENT:
        if request.user.must_change_password:
            request.session['must_change_password'] = True
            return redirect('accounts:password_change')
        if request.user.get_type_client == 3:
            return redirect("core:dashboard_student_mentorize")

        if request.user.is_authenticated and request.user.client_can_access_app:
            response = redirect(settings.FRONTEND_APP_SUBDOMAIN) # 'http://localhost:3000' # domain
            if 'authorization' in request.COOKIES:
                return response
            else:
                print('[refresh token]')
                refresh_token_obj = get_lastest_refresh_token(request.user)
                token = refresh_token(request, refresh_token_obj.token)
                set_cookie_authorization(response, token, request.session)
                return response

        return redirect("core:dashboard_student")
    elif request.user.user_type == settings.PARENT:
        if request.user.must_change_password:
            request.session['must_change_password'] = True
            return redirect('accounts:password_change')
        return redirect("core:dashboard_parent")
    elif request.user.user_type == settings.PARTNER:
        if request.user.must_change_password:
            request.session['must_change_password'] = True
            return redirect('accounts:password_change')
        return redirect("core:dashboard_partner")
    else:
        messages.error(request, "Esse usuário possui alguma inconsistência, tente novamente. Caso o erro persista entre em contato com o suporte técnico.")
        return redirect("accounts:logout")


class WebhookApiView(APIView):
    permission_classes=[AllowAny, ]

    def post(self, request, *args, **kwargs):
        client = Client.objects.get(
            pk="509e588d-e216-4dc9-92c1-c7e3572acb50"
        )

        coordination = SchoolCoordination.objects.filter(
            unity__client=client
        ).first()
        
        data = request.POST or request.data

        product_name = data.get('product_name', None) or data.get('edz_cnt_titulo', None)
        student_code = data.get('student_cod', None) or data.get('edz_cli_cod', None)
        student_name = data.get('student_name', None) or data.get('edz_cli_rsocial', None)
        student_email = data.get('student_email', None) or data.get('edz_cli_email', None)
        payment_status = data.get('recurrence_status', None) or data.get('edz_fat_status', None)
        payment_status = int(payment_status)
        
        student, created = Student.objects.get_or_create(
            name=student_name,
            client=client,
            email=student_email,
            enrollment_number=student_code
        )
        
        school_class, created = SchoolClass.objects.get_or_create(
            name=product_name,
            coordination=coordination,
            class_type=SchoolClass.REGULAR,
            school_year=timezone.localtime(timezone.now()).date().year
        )

        school_class.students.add(student)

        IN_DAY = 1
        PAID = 3
        if data.get('product_name', None):
            if payment_status == IN_DAY:
                student.user.is_active = True
                student.user.save()
            else:
                student.user.is_active = False
                student.user.save()
        elif data.get('edz_cnt_titulo', None):
            if payment_status == PAID:
                student.user.is_active = True
                student.user.save()
            else:
                student.user.is_active = False
                student.user.save()

        return Response(data= {"result": "ok"}, content_type="application/json")

webhook_new_student = WebhookApiView.as_view()

class DashboardCoordinationView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'dashboard/coordination.html'
    required_permissions = [settings.COORDINATION, ]
    has_dashboards = False
    
    def get_template_names(self) -> list[str]:
        user = self.request.user
        
        if user.is_authenticated and (user.has_perm('accounts.view_dashboards') or user.client_has_dashboards):
            return ['dashboards/details/school.html']
        
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super(DashboardCoordinationView, self).get_context_data(**kwargs)
        user = self.request.user
        today = timezone.localtime(timezone.now()).date()
        now_time = timezone.localtime(timezone.now()).time()
        
        if user.has_perm('accounts.view_dashboards') or user.client_has_dashboards:
            context["unities"] = Unity.objects.filter(
                Q(coordinations__in=user.get_coordinations_cache()),
            ).distinct()
            context["stages"] = TeachingStage.objects.annotate(
                name_length=Length('name')
            ).filter(
                client=user.client,
            ).order_by('name_length', 'name').distinct()

        context['applications_today'] = Application.objects.is_online().filter(
            Q(
                Q(school_classes__coordination__in=self.request.user.get_coordinations_cache()) |
                Q(applicationstudent__student__client__in=self.request.user.get_clients_cache())
            ),
            date=today,
            end__gte=((datetime.combine(today, now_time) - timedelta(hours=1)).time())
        ).exclude(category=Application.HOMEWORK).distinct('pk', 'start').order_by('start')

        return context

# @method_decorator([vary_on_cookie, cache_page(180)], name='dispatch')
class DashboardStudentView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'dashboard/student.html'
    required_permissions = [settings.STUDENT]
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        
        if user.is_authenticated and user.client.type_client == 3:
            return redirect(reverse('core:dashboard_student_mentorize'))
        
        return super().dispatch(request, *args, **kwargs)
    

    def get_context_data(self, **kwargs):
        context = super(DashboardStudentView, self).get_context_data(**kwargs)

        today = timezone.localtime(timezone.now()).date()
        now = timezone.localtime(timezone.now())
        seven_days_ago = now - timedelta(days=7)
        user = self.request.user

        applications_student = ApplicationStudent.objects.filter(
            Q(student__user=user)
        ).select_related('student', 'application')
        
        applications_student_launch_score = applications_student.annotate(
            datetime_end=Case(
                When(
                    application__student_stats_permission_date__lt=F('application__date_end') + F('application__end'),
                    then=F('application__student_stats_permission_date')
                ),
                default=F('application__date_end') + F('application__end'),
                output_field=DateTimeField()
            ),
            can_see=Case(
                When(
                    application__category=Application.MONITORIN_EXAM,
                    end_time__isnull=False,
                    then=Value(True)
                ),
                When(
                    application__category=Application.PRESENTIAL,
                    is_omr=True,
                    then=Value(True)
                ),
                When(
                    application__category=Application.HOMEWORK,
                    datetime_end__lt=now,
                    then=Value(True)
                ),
                default=Value(False),
                output_field=BooleanField(),
            ),
        ).filter(
            # Q(performances__isnull=False), # TODO: Removi por que ta pesando muito e não faz diferença deixar esse filtro aqui pois a performance foi aprimorada
            Q(application__student_stats_permission_date__gt=seven_days_ago),
            Q(application__student_stats_permission_date__lte=now),
            Q(can_see=True),
            Q(
                Q(application__duplicate_application=False) |
                Q(is_omr=True)
            )
        ).order_by('end_time', '-application__student_stats_permission_date')[:5]

        application_date_start = ExpressionWrapper(F('application__date') + F('application__start'), output_field=fields.DurationField())
        application_date_end = ExpressionWrapper(F('application__date') + F('application__end'), output_field=fields.DurationField())

        applications_today = applications_student.is_online().annotate(
            application_date_start=application_date_start,
            application_date_end=application_date_end,
        ).filter(
            Q(application__date=today),
            Q(
                Q(application__duplicate_application=False) |
                Q(is_omr=True)
            )
        ).exclude(application__category=Application.HOMEWORK).distinct()

        applications_homework = applications_student.is_online().annotate(
            application_date_start=application_date_start,
            application_date_end=ExpressionWrapper(
                (
                    F('application__date_end') + F('application__end')) + timedelta(hours=3), 
                    output_field=fields.DurationField()
                ),
        ).filter(
            Q(application__category=Application.HOMEWORK),
            Q(
                Q(application__duplicate_application=False) |
                Q(is_omr=True)
            ),
            Q(
                Q(application_date_end__gte=now) | Q(custom_time_finish__gte=now)
            ),
            Q(application_date_start__lte=now),
        ).exclude(
            Q(application__student_stats_permission_date__lt=now)
        ).distinct()

        apps_today_pks = applications_today.union(applications_homework).values_list("pk", flat=True)
        
        context['applications_today'] = ApplicationStudent.objects.filter(
            pk__in=apps_today_pks
        ).distinct().order_by('application__exam__name')

        applications_future = applications_student.is_online().filter(
            Q(application__date__gt=today),
            Q(
                Q(application__duplicate_application=False) |
                Q(is_omr=True)
            )
        ).distinct().order_by('application__date', 'application__start')[:5]
        
        context['applications_future'] = applications_future
        context['applications_student_launch_score'] = applications_student_launch_score
        context['student'] = user.student

        if applications_homework or applications_today.filter(application__category=Application.MONITORIN_EXAM).count():
            context['has_online_application_today'] = True

        # context['knowledge_areas'] = KnowledgeArea.objects.student_general_report(student)

        return context
class DashboardInspectorView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'dashboard/inspector.html'
    required_permissions = [settings.INSPECTOR, ]

    def get_context_data(self, **kwargs):
        context = super(DashboardInspectorView, self).get_context_data(**kwargs)

        today = timezone.localtime(timezone.now())

        context['applications_today'] = Application.objects.is_online().filter(
            inspectors__user=self.request.user,
            date=today
        ).exclude(category=Application.HOMEWORK).order_by('start')

        context['applications_future'] = Application.objects.is_online().filter(
            inspectors__user=self.request.user,
            date__gt=today
        ).exclude(category=Application.HOMEWORK).order_by('date', 'start')

        return context


class DashboardTeacherView(LoginRequiredMixin, CheckHasPermission, UserPassesTestMixin, ExamTeacherSubjectMixin, TemplateView):
    template_name = 'dashboard/teacher.html'
    required_permissions = [settings.TEACHER, ]
    
    def get_template_names(self):
        if version := self.request.GET.get('v'):
            return f'dashboard/teacher_v2.html'
        return super().get_template_names()
    
    def test_func(self):
        user = self.request.user
        return not user.is_freemium

    def get_context_data(self, **kwargs):
        context = super(DashboardTeacherView, self).get_context_data(**kwargs)

        today = timezone.localtime(timezone.now())
        seven_days_ago = today - timedelta(days=7)
        
        user = self.request.user
        teacher = user.inspector
        
        context["unities"] = Unity.objects.filter(
            Q(coordinations__in=user.get_coordinations_cache()),
        ).distinct()
        context["stages"] = TeachingStage.objects.annotate(
            name_length=Length('name')
        ).filter(
            client=user.client,
        ).order_by('name_length', 'name').distinct()
        
        recents_exams_applied = Exam.objects.annotate(
            date_end=ExpressionWrapper(F('application__date') + F('application__end'), output_field=fields.DurationField()),
            homework_date_end=ExpressionWrapper(F('application__date_end') + F('application__end'), output_field=fields.DurationField()),
        ).filter(
            Q(
                Q(application__category=Application.MONITORIN_EXAM, date_end__gt=seven_days_ago, date_end__lte=today) |
                Q(application__category=Application.HOMEWORK, homework_date_end__gt=seven_days_ago, homework_date_end__lte=today)
            ),
            teacher_subjects__teacher=teacher,
        ).distinct()
        
        exams = Exam.objects.filter(
            teacher_subjects__teacher=teacher,
            created_at__year=timezone.now().year
        )
        
        context['exams_count'] = exams.filter(~Q(category=Exam.HOMEWORK)).count()
        context['homeworks_count'] = exams.filter(Q(category=Exam.HOMEWORK)).count()

        context['applications_today'] = Application.objects.is_online().filter(
            inspectors__user=user,
            date=today
        ).exclude(category=Application.HOMEWORK).order_by('start')

        context['applications_future'] = Application.objects.is_online().filter(
            inspectors__user=user,
            date__gt=today
        ).exclude(category=Application.HOMEWORK).order_by('start')
        
        context['recents_exams_applied'] = recents_exams_applied[:4]
        
        opened_exams = self.get_exams().select_related('teacher_subject', 'teacher_subject__subject')
        
        opened_exams_not_bag = opened_exams.exclude( 
            Q(Q(exam__application__answer_sheet__isnull=False) & ~Q(exam__application__answer_sheet="")) |
            Q(Q(exam__application__room_distribution__exams_bag__isnull=False) & ~Q(exam__application__room_distribution__exams_bag=""))
        ).distinct()

        exam_questions = ExamQuestion.objects.filter(exam_teacher_subject__in=opened_exams).distinct()

        exams_total_reproved_count  = StatusQuestion.objects.filter(
            exam_question__in=exam_questions,
            status=StatusQuestion.REPROVED
        ).values('exam_question').distinct().count()

        exams_total_pendence_corretion_count  = StatusQuestion.objects.filter(
            exam_question__in=exam_questions,
            status=StatusQuestion.CORRECTION_PENDING
        ).values('exam_question').distinct().count()

        performances = GenericPerformancesFollowUp.objects.filter(
            quantity__gt=0,
            deadline__gte=timezone.localtime(timezone.now()),
            inspectors=teacher,
            coordination__in=user.get_coordinations_cache(),
        ).order_by('-quantity').distinct()
        
        exams_await_correction = performances.values('object_id').annotate(
            quantity=Sum('quantity'),
            exam_pk=F('object_id'),
            exam_name=Subquery(
                Exam.objects.filter(pk=OuterRef('object_id')).values('name')[:1]
            ),
        ).values('quantity', 'deadline', 'exam_pk', 'exam_name')

        exams_in_review_pdf = ExamQuestion.objects.filter(
            exam__status=Exam.PDF_REVIEW, 
            exam_teacher_subject__teacher_subject__teacher=teacher, 
            exam__review_deadline_pdf__gte=timezone.now()
        ).distinct()

        exam_ids = exams_in_review_pdf.values_list('exam', flat=True)

        applications_with_answer_sheets = Application.objects.exclude(
            Q(answer_sheet__isnull=False) & Q(answer_sheet="") 
        ).filter(
            exam__in=exam_ids
        )
        exams_in_review_pdf = exams_in_review_pdf.exclude(
            Exists(applications_with_answer_sheets)
        )
    
        opened_exams_pdf_review_counts = StatusQuestion.objects.filter(
            exam_question__in=exams_in_review_pdf,
            user=user
        ).filter(
            Q(status=StatusQuestion.APPROVED) |
            Q(status=StatusQuestion.REPROVED) |
            Q(status=StatusQuestion.CORRECTION_PENDING) |
            Q(status=StatusQuestion.CORRECTED) |
            Q(status=StatusQuestion.ANNULLED) |
            Q(status=StatusQuestion.SEEN) |
            Q(status=StatusQuestion.USE_LATER) |
            Q(status=StatusQuestion.DRAFT) |
            Q(status=StatusQuestion.RESPONSE)
        ).values_list('exam_question', flat=True).distinct() 

        unreviewed_exam_questions = exams_in_review_pdf.exclude(id__in=opened_exams_pdf_review_counts)
        all_perndence_pdf_review_count = unreviewed_exam_questions.values_list("exam__id", flat=True).distinct().count()

        context['all_perndence_pdf_review_count'] = all_perndence_pdf_review_count
        context['exams_total_pendence_corretion_count'] = exams_total_pendence_corretion_count
        context['exams_total_reproved_count'] = exams_total_reproved_count
        context['exams_await_correction'] = exams_await_correction[:4]
        context['exams_await_correction_count'] = exams_await_correction.count()
        context['pendent_corrections_count'] = performances.aggregate(Sum('quantity')).get('quantity__sum') or 0
        context['opened_exams'] = opened_exams_not_bag.exclude(status='Análise')[:4]
        context['all_opened_exams_count'] = opened_exams_not_bag.exclude(status='Análise').count()
        context['opened_exams_count'] = opened_exams_not_bag.exclude(status='Análise').count()
        context['await_correction'] = opened_exams_not_bag.filter(count_peding_questions__gt=0).count()
        context['is_lates_count'] = opened_exams_not_bag.filter(status='Atrasada').count()
        
        # CARDS DO DASHBOARD
        # ELABORATION
        elaboration_solicited_quantity = opened_exams_not_bag.aggregate(total=Sum('quantity')).get('total') or 0
        inserted_inserted_quantity = opened_exams_not_bag.aggregate(total=Sum('count_total_questions')).get('total') or 0
        await_insert = elaboration_solicited_quantity - inserted_inserted_quantity
        elaboration_performance = (inserted_inserted_quantity / elaboration_solicited_quantity if elaboration_solicited_quantity else 0) * 100
        context['elaboration'] = {
            'soliciteds': elaboration_solicited_quantity,
            'complete': inserted_inserted_quantity,
            'incomplete': await_insert if await_insert > 0 else 0,
            'performance':  100 if elaboration_solicited_quantity <= 0 or elaboration_performance > 100 else elaboration_performance,
        }
        
        # REVIEWS
        exams_to_review = teacher.get_exams_to_review(return_exam_teacher_subjects=True).annotate(
            count=Count('examquestion', distinct=True),
            count_reviewed_questions=Count(
                'exam__examquestion', 
                filter=Q(
                    Q(exam__examquestion__statusquestion__user=user),
                    Q(
                        Q(exam__examquestion__statusquestion__active=True) |
                        Q(exam__examquestion__statusquestion__status=StatusQuestion.SEEN)
                    )
                ), 
                distinct=True
            )
        ).filter(count__gt=0).exclude(count_reviewed_questions__gt=F('count'))

        review_solicited_quantity = exams_to_review.aggregate(total=Sum('count')).get('total') or 0
        reviewed_quantity = exams_to_review.aggregate(total=Sum('count_reviewed_questions')).get('total') or 0
        reviews_await_insert = review_solicited_quantity - reviewed_quantity
        reviews_performance = (reviewed_quantity / review_solicited_quantity if review_solicited_quantity else 0) * 100
        
        context['reviews'] = {
            'soliciteds': review_solicited_quantity,
            'complete': reviewed_quantity,
            'incomplete': reviews_await_insert if reviews_await_insert > 0 else 0,
            'performance':  100 if review_solicited_quantity <= 0 or reviews_performance > 100 else reviews_performance,
        }
        
        corrections = GenericPerformancesFollowUp.objects.filter(
            type=GenericPerformancesFollowUp.ANSWERS, 
            quantity__gt=0,
            inspectors=teacher,
            deadline__gte=timezone.localtime(today),
            coordination__in=user.get_coordinations_cache(),
        ).distinct()

        corrections_solicited_quantity = corrections.aggregate(total=Sum('total')).get('total') or 0
        corrections_quantity = corrections.aggregate(total=Sum('quantity')).get('total') or 0
        corrections_await_insert = corrections_solicited_quantity - corrections_quantity
        corrections_performance = (corrections_quantity / corrections_solicited_quantity if corrections_solicited_quantity else 0) * 100

        context['corrections'] = {
            'soliciteds': corrections_solicited_quantity,
            'complete': corrections_quantity,
            'incomplete': corrections_await_insert if corrections_await_insert > 0 else 0,
            'performance':  100 if corrections_solicited_quantity <= 0 or corrections_performance > 100 else corrections_performance,
        }
        
        context['classes_ids'] = teacher.get_classes().values_list('id', flat=True)
        
        return context

class DashboardGenericTeacherView(LoginRequiredMixin, CheckHasPermission, UserPassesTestMixin, ExamTeacherSubjectMixin, TemplateView):
    template_name = 'dashboards/details/teacher.html'
    required_permissions = [settings.TEACHER, ]
    who_id = None
    who = None
    
    def dispatch(self, request, *args, **kwargs):
        who = request.GET.get('who')

        whos = {
            'alunos': 'student', 
            'student': 'student',
            'turmas': 'classe', 
            'classe': 'classe',
            'professores': 'teacher',
            'teacher': 'teacher',
            'exam': 'teacher',
            'exams': 'teacher',
            'cadernos': 'teacher',
        }
        
        self.who = whos[who] if who else 'teacher'
        if self.request.user.is_authenticated:
            self.who_id = self.request.GET.get('who_id') if self.request.GET.get('who_id') else str(self.request.user.inspector.id)
        
        return super().dispatch(request, *args, **kwargs)
    
    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.has_perm('accounts.view_dashboards') or user.client_has_dashboards)

    def get_object(self):

        if self.who == 'student':
            return Student.objects.get(pk=self.who_id)
        elif self.who == 'classe':
            return SchoolClass.objects.get(pk=self.who_id)
        
        return self.request.user.inspector
    
    def get_context_data(self, **kwargs):
        
        user = self.request.user
        context = super().get_context_data(**kwargs)
        context["object"] = self.get_object()
        context["who"] = self.who
        context["who_id"] = self.who_id
        context["what"] = self.request.GET.get('what')
        context["what_ids"] = self.request.GET.get('what_ids')
        context["period"] = self.request.GET.get('period')
        context["classes"] = list([str(classe.id) for classe in user.inspector.get_classes()])
        context["subjects"] = list([str(subject['id']) for subject in user.inspector.subjects.filter(teachersubject__active=True).values('id')])
        
        context["unities"] = Unity.objects.filter(
            Q(coordinations__in=user.get_coordinations_cache()),
        ).distinct()
        
        return context

@login_required
@csrf_exempt
def upload_image(request):
    from django.conf import settings
    from django.core.files.storage import FileSystemStorage
    from fiscallizeon.core.storage_backends import PublicMediaStorage

    if request.method == 'POST' and request.FILES['file']:
        myfile = request.FILES['file']
        if settings.DEBUG:
            fs = FileSystemStorage()
        else:
            fs = PublicMediaStorage()

        filename = fs.save(myfile.name, myfile)
        uploaded_file_url = fs.url(filename)

        return JsonResponse({'location': uploaded_file_url}, safe=True)

    return JsonResponse({'empty': True})


@login_required
@csrf_exempt
def upload_image_paste(request):
    from django.conf import settings
    from django.core.files.storage import FileSystemStorage
    from fiscallizeon.core.storage_backends import PublicMediaStorage
    
    image_url = request.POST.get('imageUrl') 

    if request.method == 'POST' and image_url:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status() 

        file_name =  "image-paste-" + os.path.basename(image_url)
        if settings.DEBUG:
            fs = FileSystemStorage()
        else:
            fs = PublicMediaStorage()
        file_path = fs.save(file_name, ContentFile(response.content))

        uploaded_file_url = fs.url(file_path)
        
        return JsonResponse({'location': uploaded_file_url}, safe=True)

@login_required
@csrf_exempt
def upload_image_to_generate_question_with_AI(request):
    from django.conf import settings
    from fiscallizeon.core.storage_backends import PublicMediaStorage, PrivateMediaStorage

    if request.method == 'POST' and request.FILES['file']:
        myfile = request.FILES['file']
        if settings.DEBUG:
            fs = PrivateMediaStorage()
        else:
            fs = PublicMediaStorage()

        filename = fs.save(myfile.name, myfile)
        uploaded_file_url = fs.url(filename)

        return JsonResponse({'location': uploaded_file_url}, safe=True)

    return JsonResponse({'empty': True})

@login_required
@csrf_exempt
def image_proxy(request):
    from django.conf import settings
    from django.core.files.storage import FileSystemStorage
    from fiscallizeon.core.storage_backends import PublicMediaStorage
    if request.method == 'GET':
        
        image_url = request.GET.get('url')
        
        response = requests.get(image_url, timeout=10)
        response.raise_for_status() 

        file_name =  "image-proxy-" + os.path.basename(image_url)
        
        if settings.DEBUG:
            fs = FileSystemStorage()
        else:
            fs = PublicMediaStorage()
            
        file_path = fs.save(file_name, ContentFile(response.content))

        uploaded_file_url = fs.url(file_path)

        return HttpResponse(response.content, content_type=response.headers['Content-Type'])
    else:
        
        return HttpResponse(status=405)

class FindThemes(TemplateView):
    template_name = 'find-themes.html'   


class TmpAnswerPage(TemplateView):
    template_name = 'mail_template/send_teacher_show_results.html'

    def get_context_data(self, **kwargs):
        from fiscallizeon.inspectors.models import Inspector
        context =  super().get_context_data(**kwargs)
        Exam = apps.get_model('exams', 'Exam')
        FileAnswer = apps.get_model('answers', 'FileAnswer')
        data = []
        inspector_id = self.kwargs['inspector_id'] if self.kwargs['inspector_id'] else "81a77678-82ca-48d2-9458-0cfab961ff13"
        inspector = get_object_or_404(Inspector.objects.all(), pk=inspector_id)
       


        answers = FileAnswer.objects.filter(
            student_application__application__exam__teaching_stage_id="fc0361b8-6fcb-4fd4-a33b-61671887e3fc", #p5 decisão
            who_corrected=inspector.user,
            created_at__year=2024
        )
        exams_pks = list(answers.values_list('student_application__application__exam_id', flat=True).distinct())
        exams = Exam.objects.filter(id__in=exams_pks, created_at__year=2024).distinct()
        for exam in exams.order_by('name'):
            classes = answers.filter(
                student_application__application__exam_id=str(exam.pk),
            ).values('student_application__student__classes')
            school_classes = SchoolClass.objects.filter(
                pk__in=classes,
                school_year=2024
            ).distinct()
            for c in school_classes.order_by('name'):
                data.append({
                    "exam_name": exam.name,
                    "exam_id": str(exam.pk),
                    "class_name": c.name,
                    "class_id": str(c.pk),
                    "unity_name": c.coordination.unity.name,
                })

        print(data)

        context['inspector'] = inspector
        context['data'] = data
        context['BASE_URL'] = settings.BASE_URL

        return context

    
    
class DashboardParentView(LoginRequiredMixin, CheckHasPermission, ExamTeacherSubjectMixin, TemplateView):
    template_name = 'dashboard/parent.html'
    required_permissions = [settings.PARENT]
    childrens = None
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if user.is_authenticated and hasattr(user, 'parent'):
            self.childrens = user.parent.students.all()
        
        # Remover a linha caso queira enviar o pai direto para a listagem de aplicações caso ele só tenha um filho
        # if self.childrens.count() == 1:
        #     return redirect(reverse('parents:children-applications-list', kwargs={ "pk": self.childrens.first().id }))
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["childrens"] = self.childrens
        
        return context

class DashboardPartnerView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'dashboard/partner.html'
    required_permissions = [settings.PARTNER]
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        user = self.request.user
        if user.partner:
            context['is_printing_staff'] = user.partner.is_printing_staff
            
        return context 

class DashboardFreemiumView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'dashboard/freemium.html'
    user = None
    
    def test_func(self):
        self.user = self.request.user
        
        return self.user.is_freemium
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        exams = self.user.get_exams()
        
        context['subjects'] = Subject.objects.filter(pk__in=exams.values('teacher_subjects__subject')).distinct()
        context['grades'] = Grade.objects.filter(pk__in=exams.values('examteachersubject__grade')).distinct()
        
        filtred_exams = ExamTeacherSubject.objects.filter(exam__in=exams).distinct()
        
        if self.request.GET.getlist('q_subjects'):
            context['q_subjects'] = self.request.GET.getlist('q_subjects')
            filtred_exams = filtred_exams.filter(teacher_subject__subject__in=self.request.GET.getlist('q_subjects'))
            
        if self.request.GET.getlist('q_grades'):
            context['q_grades'] = self.request.GET.getlist('q_grades')
            filtred_exams = filtred_exams.filter(grade__in=self.request.GET.getlist('q_grades'))
            
        context['exams'] = filtred_exams
        
        return context



class CustomAcquireUserView(AcquireUserView, CheckHasPermission):
    permission_required = 'accounts.can_use_hijack'
    required_permissions = [settings.COORDINATION]

    def test_func(self):
        hijacker = self.request.user
        hijacked = self.get_object()

        hijacker_client = hijacker.client
        hijacked_client = hijacked.client

        return (hijacked_client.pk == hijacker_client.pk)

    def get_success_url(self):
        return reverse('core:redirect_dashboard')


def analytics_coordination(request):
    return render(request, 'analytics/index.html')


def analytics_detail_coordination(request):
    return render(request, 'analytics/detail.html')

class SwitchUserProfileView(LoginRequiredMixin, View):
   def post(self, request):
        user = request.user
        try:
            CACHE_KEY = f'USER_TYPE_{user.pk}'
            Inspector = apps.get_model("inspectors", "Inspector")

            if user.user_type == settings.TEACHER:
                inspector = Inspector.objects.get(user=user)
                inspector.can_access_coordinator_profile = True
                inspector.save()
                cache.set(CACHE_KEY, settings.COORDINATION) 
            else:
                inspector = Inspector.objects.get(user=user)
                inspector.can_access_coordinator_profile = False
                inspector.save()
                cache.set(CACHE_KEY, settings.TEACHER) 

            messages.success(request, f"Perfil alterado com sucesso")
        except Exception as e:
            print(e)
            messages.error(request, f"Não foi possível alternar entre os perfis. Por favor, tente novamente.")

        return redirect('core:redirect_dashboard') 

status = Healthcheck.as_view()
dashboard_coordination = DashboardCoordinationView.as_view()
dashboard_student = DashboardStudentView.as_view()
dashboard_inspector = DashboardInspectorView.as_view()
dashboard_teacher = DashboardTeacherView.as_view()
dashboard_parent = DashboardParentView.as_view()
dashboard_partner = DashboardPartnerView.as_view()

terms = TermsView.as_view()

