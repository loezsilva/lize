from django.urls import reverse
from django.contrib import messages
from django.conf import settings
from django.utils import timezone
from django.http import HttpResponseRedirect

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from fiscallizeon.classes.models import Grade, SchoolClass
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.exams.models import ExamTeacherSubject
from fiscallizeon.core.print_colors import *

from fiscallizeon.core.utils import CheckHasPermission

from .models import StudyMaterial
from .forms import StudyMaterialForm, StudyMaterialUpdateForm
from fiscallizeon.exams.models import Exam
from fiscallizeon.subjects.models import Subject
from django.db.models import Q

class StudyMaterialCreate(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    template_name = 'materials/study_material_create_update.html'
    model = StudyMaterial
    permission_required = 'materials.add_studymaterial'
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    form_class = StudyMaterialForm
    success_message = 'Material adicionado com sucesso'

    def get_form_kwargs(self):
        kwargs = super(StudyMaterialCreate, self).get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs
    
    def get_context_data(self, **kwargs):
        today = timezone.localtime(timezone.now())
        context = super().get_context_data(**kwargs)
        
        context["grades"] = Grade.objects.all()
        
        
        if self.request.user.user_type == settings.TEACHER:
            inspector_instance = Inspector.objects.filter(user=self.request.user).first()

            # Busca as pks da classes que o teacher tem vínculo
            classes_he_teacher = inspector_instance.teachersubject_set.all().values_list('classes__pk', flat=True)
            context["school_classes"] = SchoolClass.objects.filter(
                coordination__in=self.request.user.get_coordinations_cache(),
                school_year=today.year,
                pk__in=classes_he_teacher
            ).distinct()

            context["exams"] = Exam.objects.filter(
                coordinations__in=self.request.user.get_coordinations(),
                examteachersubject__teacher_subject__teacher__user=self.request.user,
            )

        else:

            context["school_classes"] = SchoolClass.objects.filter(
                coordination__in=self.request.user.get_coordinations_cache(),
                school_year=today.year
            ).distinct()

            context["exams"] = Exam.objects.filter(
                coordinations__in=self.request.user.get_coordinations()
            )

        context['year'] = today.year

        return context

    def form_valid(self, form: StudyMaterialForm):

        if form.cleaned_data['exam']:
            form.cleaned_data['subjects'] = []
            form.cleaned_data['school_classes'] = []
            form.cleaned_data['grades'] = []

        form.instance.send_by = self.request.user

        return super().form_valid(form)
        
    def get_success_url(self):
        return reverse('materials:study_material_list')

class StudyMaterialUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    template_name = 'materials/study_material_create_update.html'
    model = StudyMaterial
    permission_required = 'materials.change_studymaterial'
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    form_class = StudyMaterialUpdateForm
    success_message = 'Material atualizado com sucesso'

    def get_form_kwargs(self):
        kwargs = super(StudyMaterialUpdateView, self).get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs
    
    def get_context_data(self, **kwargs):
        today = timezone.localtime(timezone.now())
        context = super().get_context_data(**kwargs)
        
        context["grades"] = Grade.objects.all()

        if self.request.user.user_type == settings.TEACHER:
            inspector_instance = Inspector.objects.filter(user=self.request.user).first()
            classes_he_teacher = inspector_instance.teachersubject_set.all().values_list('classes__pk', flat=True)

            context["school_classes"] = SchoolClass.objects.filter(
                coordination__in=self.request.user.get_coordinations_cache(),
                school_year=today.year,
                pk__in=classes_he_teacher
            ).distinct()

        else:
            context["school_classes"] = SchoolClass.objects.filter(
                coordination__in=self.request.user.get_coordinations_cache(),
                school_year=today.year
            ).distinct()

        context['year'] = today.year

        return context

    def form_valid(self, form: StudyMaterialUpdateForm):
        if form.cleaned_data['exam']:
            form.cleaned_data['subjects'] = []
            form.cleaned_data['school_classes'] = []
            form.cleaned_data['grades'] = []

        return super(StudyMaterialUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('materials:study_material_list')

class StudyMaterialListView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, ListView):
    template_name = 'materials/study_material_list.html'
    permission_required = 'materials.view_studymaterial'
    model = StudyMaterial
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    paginate_by = 10

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_study_material:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super(StudyMaterialListView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super(StudyMaterialListView, self).get_queryset()
        queryset = queryset.filter(client__in=self.request.user.get_clients_cache())

        if self.request.user.user_type == settings.TEACHER:
            queryset = queryset.filter(send_by=self.request.user)
        
        if self.request.GET.get('title'):
            queryset = queryset.filter(
                title__icontains=self.request.GET.get('title', "")
            )
        if self.request.GET.get('q_subjects'):
            queryset = queryset.filter(
                subjects__in=self.request.GET.getlist('q_subjects', "")
            )             
        if self.request.GET.get('q_stage'):
            queryset = queryset.filter(
                stage__in=self.request.GET.getlist('q_stage', "")
            )         

        if self.request.GET.get('q_classes'):
            queryset = queryset.filter(
                school_classes__in=self.request.GET.getlist('q_classes', "")
            )
        if self.request.GET.get('q_has_exam'):
            queryset = queryset.filter(
                exam__isnull=False
            )
        
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super(StudyMaterialListView, self).get_context_data(**kwargs)
        
        context['title'] = self.request.GET.get('title', "")
        context['q_subjects'] = self.request.GET.getlist('q_subjects', "")
        context['q_stage'] = self.request.GET.getlist('q_stage', "")
        context['q_classes'] = self.request.GET.getlist('q_classes', "")
        context['q_has_exam'] = self.request.GET.getlist('q_has_exam', "")
        
        list_filters = [context['title'], context['q_subjects'], context['q_classes'], context['q_stage'], context['q_has_exam']]
        
        context['count_filters'] = len(list_filters) - list_filters.count("")
        
        context['classes'] = SchoolClass.objects.filter(
            coordination__in=self.request.user.get_coordinations_cache(),
            school_year=timezone.now().year
        ).order_by('name').distinct()
        
        context['subjects'] = Subject.objects.filter(
            Q(parent_subject__isnull=True) |
            Q(client__isnull=True) |
            Q(
                Q(parent_subject__isnull=False) &
                Q(client__in=self.request.user.get_clients_cache())
            )
        ).order_by('name').distinct()
        
        return context

class StudyMaterialDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = StudyMaterial
    permission_required = 'materials.delete_studymaterial'
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    success_message = "Cabeçalho removido com sucesso!"

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER', None)
# Material End

study_material_create = StudyMaterialCreate.as_view()
study_material_update = StudyMaterialUpdateView.as_view()
study_material_delete = StudyMaterialDeleteView.as_view()
study_material_list = StudyMaterialListView.as_view()
