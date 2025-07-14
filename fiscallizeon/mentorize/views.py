import json
from statistics import fmean
from django.contrib.auth.mixins import LoginRequiredMixin
import numpy as np
from fiscallizeon.core.utils import CheckHasPermission
from django.views.generic import TemplateView, ListView, DetailView

from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.db.models import (
    Q, F, ExpressionWrapper, fields, DateTimeField, Case, When, Value, BooleanField
)
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.students.models import Student
from fiscallizeon.subjects.models import Subject, Topic
import decimal

from django.shortcuts import redirect
from django.urls import reverse



class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)
    
# Create your views here.
class DashboardStudentView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'mentorize/students/student.html'
    required_permissions = [settings.STUDENT, ]
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        
        if user.is_authenticated and not user.get_clients().first().type_client == 3:
            return redirect(reverse('core:dashboard_student'))
        
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DashboardStudentView, self).get_context_data(**kwargs)

        today = timezone.localtime(timezone.now()).date()
        now = timezone.localtime(timezone.now())
        seven_days_ago = now - timedelta(days=7)
        
        if self.request.GET.get('recalculate'):
            self.request.user.student.run_recalculate_performances()
            
        if self.request.GET.get('create_lists'):
            self.request.user.student.create_lists()
            
        applications_student_launch_score = ApplicationStudent.objects.filter(
            Q(performances__isnull=False),
            Q(student__user=self.request.user),
            Q(end_time__gt=seven_days_ago),
            Q(end_time__lte=now),
            Q(
                Q(application__duplicate_application=False) |
                Q(is_omr=True)
            )
        ).distinct().order_by('-end_time')[:5]


        application_date_start = ExpressionWrapper(F('application__date') + F('application__start'), output_field=fields.DurationField())
        application_date_end = ExpressionWrapper(F('application__date') + F('application__end'), output_field=fields.DurationField())

        applications_today = ApplicationStudent.objects.is_online().annotate(
            application_date_start=application_date_start,
            application_date_end=application_date_end,
        ).filter(
            Q(student__user=self.request.user),
            Q(application__date=today),
            Q(
                Q(application__duplicate_application=False) |
                Q(is_omr=True)
            )
        ).exclude(application__category=Application.HOMEWORK)

        applications_homework = ApplicationStudent.objects.is_online().annotate(
            application_date_start=application_date_start,
            application_date_end=ExpressionWrapper(
                (
                    F('application__date_end') + F('application__end')) + timedelta(hours=3), 
                    output_field=fields.DurationField()
                ),
        ).filter(
            Q(student__user=self.request.user),
            Q(application__category=Application.HOMEWORK),
            Q(application_date_start__lte=now),
            Q(application_date_end__gte=now),
            Q(
                Q(application__duplicate_application=False) |
                Q(is_omr=True)
            )
        ).exclude(end_time__isnull=False)
        
        context['applications_today'] = ApplicationStudent.objects.filter(pk__in=applications_today.union(applications_homework).values_list('pk', flat=True)).distinct().order_by('-application__priority', 'application__start')

        applications_future = ApplicationStudent.objects.is_online().filter(
            Q(student__user=self.request.user),
            Q(application__date__gt=today),
            Q(
                Q(application__duplicate_application=False) |
                Q(is_omr=True)
            )
        ).distinct().order_by('application__start')

        student = Student.objects.get(user=self.request.user)
        
        subjects_data = []
        
        subjects = Subject.objects.filter(performances__student=student).distinct()
        
        for subject in subjects:
            
            subject_performance = subject.last_performance(student=self.request.user.student).first()
            
            data = {
                "id": str(subject.pk),
                "name": subject.__str__(),
                "performance": float(subject_performance.performance) if subject_performance else 0,
                "topics": [],
                "abilities": [],
                "competences": [],
                "loads": {
                    "topics": 'false',
                    "abilities": 'false',
                    "competences": 'false',
                }
            }
            subjects_data.append(data)
        
        context['applications_future'] = applications_future
        context['applications_student_launch_score'] = applications_student_launch_score
        context['student'] = student
        context['subjects'] = subjects_data

        # context['knowledge_areas'] = KnowledgeArea.objects.student_general_report(student)

        return context

class DashboardStudentFirstAccessView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'mentorize/students/student-first-access.html'
    required_permissions = [settings.STUDENT, ]
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        
        if user.is_authenticated and not user.get_clients().first().type_client == 3:
            return redirect(reverse('core:dashboard_student'))
        
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DashboardStudentFirstAccessView, self).get_context_data(**kwargs)

        today = timezone.localtime(timezone.now()).date()
        now = timezone.localtime(timezone.now())
        seven_days_ago = now - timedelta(days=7)

        applications_student_launch_score = ApplicationStudent.objects.annotate(
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
            Q(performances__isnull=False),
            Q(student__user=self.request.user),
            Q(application__student_stats_permission_date__gt=seven_days_ago),
            Q(application__student_stats_permission_date__lte=now),
            Q(can_see=True),
            Q(
                Q(application__duplicate_application=False) |
                Q(is_omr=True)
            )
        ).order_by('-application__student_stats_permission_date')[:5]


        application_date_start = ExpressionWrapper(F('application__date') + F('application__start'), output_field=fields.DurationField())
        application_date_end = ExpressionWrapper(F('application__date') + F('application__end'), output_field=fields.DurationField())

        applications_today = ApplicationStudent.objects.is_online().annotate(
            application_date_start=application_date_start,
            application_date_end=application_date_end,
        ).filter(
            Q(student__user=self.request.user),
            Q(application__date=today),
            Q(
                Q(application__duplicate_application=False) |
                Q(is_omr=True)
            )
        ).exclude(application__category=Application.HOMEWORK).distinct().order_by('application__start')

        applications_homework = ApplicationStudent.objects.is_online().annotate(
            application_date_start=application_date_start,
            application_date_end=ExpressionWrapper(
                (
                    F('application__date_end') + F('application__end')) + timedelta(hours=3), 
                    output_field=fields.DurationField()
                ),
        ).filter(
            Q(student__user=self.request.user),
            Q(application__category=Application.HOMEWORK),
            Q(application_date_start__lte=now),
            Q(application_date_end__gte=now),
            Q(
                Q(application__duplicate_application=False) |
                Q(is_omr=True)
            )
        ).distinct().order_by('application__start')
        
        context['applications_today'] = applications_today.union(applications_homework)

        applications_future = ApplicationStudent.objects.is_online().filter(
            Q(student__user=self.request.user),
            Q(application__date__gt=today),
            Q(
                Q(application__duplicate_application=False) |
                Q(is_omr=True)
            )
        ).distinct().order_by('application__start')

        student = Student.objects.get(user=self.request.user)
        
        context['applications_future'] = applications_future
        context['applications_student_launch_score'] = applications_student_launch_score
        context['student'] = student

        # context['knowledge_areas'] = KnowledgeArea.objects.student_general_report(student)

        return context
    
class DashboardStudentExamPreviewDetailsView(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'mentorize/exams/exam_review_details.html'
    required_permissions = [settings.STUDENT, ]
    queryset = ApplicationStudent.objects.all()
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        
        if user.is_authenticated and not user.get_clients().first().type_client == 3:
            return redirect(reverse('core:dashboard_student'))
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        from fiscallizeon.questions.models import Question
        
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        questions = Question.objects.filter(
            alternatives__is_correct=False, 
            alternatives__optionanswer__student_application__student__user=user,
            alternatives__question__subject__in=self.object.application.exam.teacher_subjects.all().values_list('subject'),
        ).distinct()
        
        context["fails_questions"] = questions
        
        topics = Topic.objects.filter(pk__in=questions.values_list('topics', flat=True)).distinct()
        
        subjects = []
        for subject in Subject.objects.filter(pk__in=self.object.application.exam.teacher_subjects.all().values_list('subject')).distinct():
            subject_object = {
                "id": subject.id,
                "name": subject.name,
                "performance": subject.last_performance(student=user.student).first().performance if subject.last_performance(student=user.student).first() else 0,
            }
            subjects.append(subject_object)
        
        context["topics"] = topics
        context["subjects"] = subjects
        
        return context
    
    
class ApplicationStudentListView(LoginRequiredMixin, CheckHasPermission, ListView):
    template_name = 'mentorize/applications/applications_student/application_student_list.html'
    required_permissions = [settings.STUDENT, ]
    model = ApplicationStudent
    paginate_by = 10  
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        
        if user.is_authenticated and not user.get_clients().first().type_client == 3:
            return redirect(reverse('applications:application_student_list'))
        
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()

        today = timezone.now().astimezone()
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
            
        if self.request.GET.get('only_scheduled'):
            queryset = queryset.filter(
                application__student_stats_permission_date__gt=today,
            )
        else:
            queryset = queryset.filter(
                application__student_stats_permission_date__lte=today
            )
            
        if self.request.user.student:
            return queryset.filter(
                student=self.request.user.student,
                application__exam__isnull=False,
            ).get_annotation_count_answers(only_total_grade=True).order_by('-created_at').distinct()

        return ApplicationStudent.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = timezone.now().astimezone()
        
        context["today"] = today
        
        context['only_scheduled'] = False
        
        context['year'] = today.year
        if self.request.GET.get('year'):
            context['year'] = self.request.GET.get('year')
            
        if self.request.GET.get('only_scheduled'):
            context['only_scheduled'] = self.request.GET.get('only_scheduled')

        if self.request.GET.get('category'):
            context['category'] = self.request.GET.get('category')
        
        return context
