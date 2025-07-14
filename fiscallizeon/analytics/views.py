import json

from django.conf import settings
from django.utils import timezone
from django.db.models import Case, When, Value, CharField
from django.db.models import Q, F
from django.db.models.functions import Concat
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib import messages
from django.db.models.aggregates import Count
from django.views.generic.base import TemplateView
from django.views.generic import ListView, DetailView
from django.http.response import HttpResponseRedirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.serializers.json import DjangoJSONEncoder

from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.clients.models import Unity
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.subjects.models import Subject
from fiscallizeon.classes.models import Grade, SchoolClass
from fiscallizeon.clients.models import EducationSystem, TeachingStage
from fiscallizeon.exams.models import Exam
from fiscallizeon.students.models import Student
from fiscallizeon.analytics.models import MetabaseDashboard


class AnalyticsTemplateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'analytics/analytics.html'
    required_permissions = ['coordination', ]
    permission_required = 'accounts.view_administration_dashboard'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated and not user.client_has_dashboard:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('applications:applications_list'))

        return super(AnalyticsTemplateView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        subjects = Subject.objects.filter()

        classes = SchoolClass.objects.filter(
            coordination__unity__client__in=self.request.user.get_clients_cache(),
            school_year=timezone.now().year
        ).annotate(students_count=Count('students')).order_by("name", )
        
        context['unitys'] = Unity.objects.filter(
            coordinations__in=self.request.user.get_coordinations()
        ).distinct()

        context['subjects'] = subjects
        context["grades"] = Grade.objects.all()
        context['classes'] = classes
        
        # Filtros
        context['q_initial_date'] = self.request.GET.get('q_initial_date', "")
        context['q_final_date'] = self.request.GET.get('q_final_date', "")
        context['q_unitys'] = self.request.GET.getlist('q_unitys', "")
        context['q_grades'] = self.request.GET.getlist('q_grades', "")
        context['q_subjects'] = self.request.GET.getlist('q_subjects', "")
        context['q_classes'] = self.request.GET.getlist('q_classes', "")
        context['q_stage'] = self.request.GET.get('q_stage', "")

        return context
    
class AnalyticsExamsTemplateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'analytics/analytics_exams.html'
    permission_required = 'accounts.view_administration_dashboard'
    required_permissions = [settings.COORDINATION, ]

    def dispatch(self, request, *args, **kwargs):

        if request.user.is_authenticated and not request.user.client_has_dashboard:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from fiscallizeon.clients.models import TeachingStage, EducationSystem
        context = super().get_context_data(**kwargs)
        today = timezone.localtime(timezone.now())
        
        subjects = Subject.objects.filter(   
            Q(parent_subject__isnull=True) |
            Q(client__isnull=True) |
            Q(
                Q(parent_subject__isnull=False) &
                Q(client__in=self.request.user.get_clients_cache())
            )
        )

        classes = SchoolClass.objects.filter(
            coordination__unity__client__in=self.request.user.get_clients_cache(),
            school_year=timezone.now().year
        ).annotate(students_count=Count('students')).order_by("name", )
        
        context['unitys'] = Unity.objects.filter(
            coordinations__in=self.request.user.get_coordinations_cache()
        ).distinct()
        
        context['teachers'] = Inspector.objects.filter(
            coordinations__in=self.request.user.get_coordinations_cache(),
            teachersubject__examteachersubject__examquestion__statusquestion__isnull=False,
        ).order_by('name').distinct()

        context['subjects'] = subjects
        context["grades"] = Grade.objects.all()
        context["teaching_stages"] = TeachingStage.objects.filter(client__in=self.request.user.get_clients_cache())
        context["education_systems"] = EducationSystem.objects.filter(client__in=self.request.user.get_clients_cache())
        context['classes'] = classes
        
        # Filtros
        context['q_initial_date'] = self.request.GET.get('q_initial_date', "")
        context['q_final_date'] = self.request.GET.get('q_final_date', "")
        context['q_teachers'] = self.request.GET.getlist('q_teachers', "")
        context['q_unitys'] = self.request.GET.getlist('q_unitys', "")
        context['q_grades'] = self.request.GET.getlist('q_grades', "")
        context['q_teaching_stages'] = self.request.GET.getlist('q_teaching_stages', "")
        context['q_education_systems'] = self.request.GET.getlist('q_education_systems', "")
        context['q_subjects'] = self.request.GET.getlist('q_subjects', "")
        context['q_classes'] = self.request.GET.getlist('q_classes', "")
        
        context['year'] = self.request.GET.get('year', None) or str(today.year) 
            
        context['q_segments'] = self.request.GET.getlist('q_segments', "")

        return context
    
class AnalyticsElitTemplateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'analytics/elit/analytics.html'
    required_permissions = [settings.COORDINATION, ]

    def dispatch(self, request, *args, **kwargs):        
        if request.user.is_authenticated and not request.user.client_has_dashboard:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super().dispatch(request, *args, **kwargs)
    
class AnalyticsRibamarTemplateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'analytics/ribamar.html'
    required_permissions = [settings.COORDINATION, ]

    def dispatch(self, request, *args, **kwargs):        
        if request.user.is_authenticated and not request.user.client_has_dashboard:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super().dispatch(request, *args, **kwargs)
    
class AnalyticsMetabaseDashboardListView(LoginRequiredMixin, CheckHasPermission, ListView):
    template_name = 'analytics/metabase/dashboards_list.html'
    required_permissions = [settings.COORDINATION, ]
    model = MetabaseDashboard

    def dispatch(self, request, *args, **kwargs):        
        if request.user.is_authenticated and not request.user.client_has_metabase_dashboard:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return super().get_queryset().filter(
            client__in=self.request.user.get_clients_cache(),
            is_active=True,
        ).order_by('created_at')

class AnalyticsMetabaseDashboardDetailView(LoginRequiredMixin, CheckHasPermission, DetailView):
    template_name = 'analytics/metabase/dashboard_detail.html'
    required_permissions = [settings.COORDINATION, ]
    model = MetabaseDashboard

    def dispatch(self, request, *args, **kwargs):        
        if request.user.is_authenticated and not request.user.client_has_metabase_dashboard:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super().dispatch(request, *args, **kwargs)


class AnalyticsENEMGovrnTemplateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'analytics/gov_rn/enem.html'
    required_permissions = [settings.COORDINATION, ]

    def dispatch(self, request, *args, **kwargs):        
        if not request.user.is_authenticated and not request.user.client_has_dashboard:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super().dispatch(request, *args, **kwargs)

class AnalyticsGAETemplateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'analytics/gae/analytics.html'
    required_permissions = [settings.COORDINATION, ]

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.client_has_dashboard:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super().dispatch(request, *args, **kwargs)
    
class AnalyticsAvhaTemplateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'analytics/avha/analytics.html'
    required_permissions = [settings.COORDINATION, ]

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.client_has_dashboard:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super().dispatch(request, *args, **kwargs)
    
class AnalyticsIdecTemplateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'analytics/idec/analytics.html'
    required_permissions = [settings.COORDINATION, ]

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.client_has_dashboard:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super().dispatch(request, *args, **kwargs)


class GradeMapTemplateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'analytics/grade_map.html'
    required_permissions = [settings.COORDINATION, ]
    permission_required = 'accounts.view_grade_map_dashboard'

    def dispatch(self, request, *args, **kwargs):        
        if request.user.is_authenticated and not request.user.client_has_dashboard:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        
        client = user.client
        coordinations = user.get_coordinations_cache()
        
        education_systems = EducationSystem.objects.filter(client=client)
        teaching_stages = TeachingStage.objects.filter(client=client)
        
        context["education_systems"] = education_systems
        context["teaching_stages"] = teaching_stages

        if self.request.GET.get("q_classe"):
            classe = SchoolClass.objects.get(pk=self.request.GET.get("q_classe"))
            context["classe"] = SchoolClass.objects.get(pk=self.request.GET.get("q_classe"))
            
            exams = Exam.objects.filter(
                Q(created_at__year=timezone.now().year),
                Q(
                    application__applicationstudent__created_at__year=timezone.now().year,
                    application__applicationstudent__student__classes=classe,
                ),
                Q(name__icontains=self.request.GET.get('q_exam')) if self.request.GET.get('q_exam') else Q(),
                Q(teaching_stage__in=self.request.GET.getlist('q_teaching_stage')) if education_systems else Q(),
                Q(education_system__in=self.request.GET.getlist('q_education_system')) if education_systems else Q(),
            ).order_by('created_at').distinct()
            

            students = Student.objects.filter(
                user__is_active=True,
                pk__in=exams.values_list('application__applicationstudent__student__pk', flat=True)
            ).order_by('name').distinct()

            exams = exams.annotate(
                missed_students_count=Count(
                    'application__applicationstudent', 
                    filter=Q(application__applicationstudent__missed=True),
                    distinct=True  
                )
            )

            students = students.annotate(
                missed_students_count=Count(
                    'applicationstudent__application', 
                    filter=Q(applicationstudent__missed=True),
                    distinct=True  
                )
            )

            exams = exams.annotate(
                empty_questions_count=Count(
                    'questions',
                    filter=Q(questions__category__in=[0,1,3], application__applicationstudent__empty_option_questions__isnull=False),
                    distinct=True
                )
            )
        

            students = students.annotate(
                empty_questions_count=Count(
                    'applicationstudent__empty_option_questions', 
                    filter=Q(applicationstudent__empty_option_questions__category__in=[0,1,3]),
                    distinct=True  
                )
            )
            context["students"]  = students
    
            context["exams"] = exams

        context["q_unity"] = self.request.GET.get('q_unity', '')
        context["q_grade"] = self.request.GET.get('q_grade', '')
        context["q_classe"] = self.request.GET.get('q_classe', '')
        context["q_exam"] = self.request.GET.get('q_exam', '')
        context["q_education_system"] = self.request.GET.getlist('q_education_system')
        context["q_teaching_stage"] = self.request.GET.getlist('q_teaching_stage')
        
        context["unities"] = json.dumps(list(Unity.objects.filter(
            coordinations__in=coordinations
        ).values('id', 'name')), cls=DjangoJSONEncoder, indent=4)
        
        context["grades"] = json.dumps(list(Grade.objects.all().annotate(
            full_name=Case(
                When(
                    Q(level=Grade.HIGHT_SCHOOL), 
                    then=Concat(F('name'), Value('ª Série'))
                ),
                default=Concat(F('name'), Value('º Ano')),
                output_field=CharField()
            )
        ).values('id', 'full_name')), cls=DjangoJSONEncoder, indent=4)
        
        context["classes"] = json.dumps(
            list(
                SchoolClass.objects.filter(
                    school_year=timezone.now().year,
                    coordination__in=coordinations
                ).annotate(
                    unity=F('coordination__unity__id')
                ).values('id', 'grade', 'unity', 'name')
            ), 
            cls=DjangoJSONEncoder, indent=4
        )
        
        return context
    

class TriTemplateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'analytics/tri.html'
    permission_required = 'accounts.view_tri_dashboard'
    required_permissions = [settings.COORDINATION, ]

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.client_has_dashboard:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        
        clients = user.get_clients_cache()
        
        context["unities"] = json.dumps(list(
            Unity.objects.filter(
                client__in=clients
            ).values('id', 'name')
        ), cls=DjangoJSONEncoder, indent=4)

        context["classes"] = json.dumps(list(SchoolClass.objects.filter(
            school_year=timezone.now().year,
            coordination__unity__client__pk__in=user.get_clients_cache()
        ).annotate(unity=F('coordination__unity__id')).values('id', 'grade', 'unity', 'name')), cls=DjangoJSONEncoder, indent=4)
        
        return context
    
class DashboardTRITemplateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'analytics/tri/dashboard_tri_v2.html'
    permission_required = 'accounts.view_tri_dashboard'
    required_permissions = [settings.COORDINATION, ]
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.client_has_tri:
            messages.warning(request, 'Cliente não possui este módulo')
            return redirect(reverse('core:redirect_dashboard'))
            
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = self.request.user        
        clients = user.get_clients_cache()
        
        exams = Exam.objects.filter(coordinations__unity__client__in=clients, application__isnull=False).distinct()
        context["exams"] = exams

        return context


class DashboardFollowUpTemplateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'analytics/follow-up/follow_up.html'
    permission_required = 'accounts.view_followup_dashboard'
    required_permissions = [settings.COORDINATION, ]
    
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.client_has_dashboard:
            messages.warning(request, 'Cliente não possui este módulo')
            return redirect(reverse('core:redirect_dashboard'))
            
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        return context


analytics_detail = AnalyticsTemplateView.as_view()