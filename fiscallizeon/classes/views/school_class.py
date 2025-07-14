from datetime import datetime
from django.conf import settings
from django.utils import timezone
from django.conf import settings

from fiscallizeon.clients.models import EducationSystem, Unity
from rest_framework import generics
from django_filters.rest_framework import DjangoFilterBackend
from django.urls import reverse

from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from rest_framework.filters import SearchFilter
from fiscallizeon.applications.models import Application

from fiscallizeon.classes.models import Grade, SchoolClass
from fiscallizeon.classes.forms import SchoolClassForm
from fiscallizeon.classes.serializers import SchoolClassSerializer, SchoolClassSimpleSerializer
from fiscallizeon.core.utils import CheckHasPermission

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q

class ClassList(LoginRequiredMixin, CheckHasPermission, ListView):
    model = SchoolClass
    required_permissions = ['coordination', ]
    permission_required = 'classes.view_schoolclass'
    paginate_by = 20
    template_name = "dashboard/classes/class_list.html"

    def get_queryset(self):
        queryset = SchoolClass.objects.filter(
            coordination__in=self.request.user.get_coordinations_cache(),
        ).order_by("coordination__unity__name", "name")

        today = timezone.localtime(timezone.now())
        
        if self.request.GET.get('year'):
            queryset = queryset.filter(
                school_year=self.request.GET.get('year'),
            )
        else:
            queryset = queryset.filter(
                school_year=today.year,
            )

        if self.request.GET.get('q_pk', ''):
            queryset = queryset.filter(pk=self.request.GET.get('q_pk', ''))

        if self.request.GET.get('q_name', ""):
            queryset = queryset.filter(
                name__icontains=self.request.GET.get('q_name', "")
            )

        if self.request.GET.get('q_temporary_class', ""):
            queryset = queryset.filter(
                temporary_class=self.request.GET.get('q_temporary_class', "")
            )

        if self.request.GET.get('q_school_year', ""):
            queryset = queryset.filter(
                school_year__icontains=self.request.GET.get('q_school_year', "")
            )

        if self.request.GET.getlist('q_grades', ""):
            queryset = queryset.filter(
                grade__pk__in=self.request.GET.getlist('q_grades', "")
            )

        if self.request.GET.getlist('q_unities', ""):
            queryset = queryset.filter(
                coordination__unity__pk__in=self.request.GET.getlist('q_unities', "")
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super(ClassList, self).get_context_data(**kwargs)
        
        today = timezone.localtime(timezone.now())
        context['q_pk'] = self.request.GET.get('q_pk', '')
        context['q_name'] = self.request.GET.get('q_name', "")
        context['q_temporary_class'] = self.request.GET.get('q_temporary_class', "")
        context['q_unities'] = self.request.GET.getlist('q_unities', "")
        context['q_grades'] = self.request.GET.getlist('q_grades', "")
        context['q_school_year'] = self.request.GET.get('q_school_year', "")

        list_filters = [context['q_name'], context['q_unities'], context["q_grades"], context['q_temporary_class'], context['q_school_year']]
        context['count_filters'] = len(list_filters) - list_filters.count("")

        user = self.request.user
        
        context['unities'] = Unity.objects.filter(
            coordinations__in=user.get_coordinations_cache()
        ).distinct()

        filter_condition = Q()
        if user.has_high_school_coordinations:
            filter_condition |= Q(level=Grade.HIGHT_SCHOOL)

        if user.has_elementary_school_only_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL)

        if user.has_elementary_school2_coordinations:
            filter_condition |= Q(level=Grade.ELEMENTARY_SCHOOL_2)
        
        context["grades"] = Grade.objects.filter(filter_condition)

        context['year'] = today.year
        
        if self.request.GET.get('year'):
            context['year'] = self.request.GET.get('year')

        return context


class SchoolClasseList(LoginRequiredMixin, CheckHasPermission, generics.ListCreateAPIView):
    queryset = SchoolClass.objects.all()
    required_permissions = [settings.COORDINATION, settings.TEACHER]
    serializer_class = SchoolClassSerializer
    filter_backends = [SearchFilter, DjangoFilterBackend]
    filterset_fields = { 
        'grade': ["in", "exact"],
        'id': ["in", "exact"],
        'coordination__unity': ["in", "exact"],
        'school_year': ['in', 'exact'],
    }
    search_fields = ['name', 'coordination__unity__name']

    def get_serializer_class(self):
        if self.request.GET.get('simple_serializer'):
            return SchoolClassSimpleSerializer
        return super().get_serializer_class()

    def get_queryset(self):
        user = self.request.user

        queryset = SchoolClass.objects.filter(
            coordination__unity__client__in=user.get_clients_cache(),
            school_year=timezone.now().year,
        ).order_by('name')
        
        if self.request.GET.get('pk', ""):
            queryset = queryset.filter(pk__in=self.request.GET.getlist('pk', ""))

        if self.request.GET.get('year'):
            queryset = queryset.filter(
                school_year=self.request.GET.get('year'),
            )

        if self.request.GET.get('system'):
            system = EducationSystem.objects.get(pk=self.request.GET.get('system'))

            queryset = queryset.filter(coordination__unity__in=system.unities.all())
        
        if self.request.GET.get('turn'):
            queryset = queryset.filter(turn=self.request.GET.get('turn'))

        
        if user.user_type == settings.TEACHER: # NÃO REMOVER ESTA QUERY
            queryset = queryset.filter(
                Q(
                    teachersubject__active=True,
                    teachersubject__teacher=user.inspector,
                ),
                Q(teachersubject__subject=self.request.GET.get('subject')) if self.request.GET.get('subject') else Q()
            )
        
        return queryset.distinct()

class ClassCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    model = SchoolClass
    required_permissions = ['coordination', ]
    permission_required = 'classes.add_schoolclass'
    form_class = SchoolClassForm
    template_name = "dashboard/classes/class_create_update.html"
    success_message = "Turma cadastrada com sucesso!"

    def get_success_url(self):
        return reverse('classes:classes_list')

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super(ClassCreateView, self).get_form_kwargs(*args, **kwargs)
        form_kwargs['user'] = self.request.user
        return form_kwargs

class ClassUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    model = SchoolClass
    required_permissions = ['coordination', ]
    permission_required = 'classes.change_schoolclass'
    form_class = SchoolClassForm
    template_name = "dashboard/classes/class_create_update.html"
    success_message = "Turma atualizada com sucesso!"

    def form_valid(self, form):
        applications = Application.objects.filter(pk__in=form.instance.applications.all())

        for application in applications.all():
                if not application.is_time_finished:
                    for student in list(form.cleaned_data['students']):
                        if student not in application.students.all():
                            application.students.add(student)
        
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('classes:classes_list')

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super(ClassUpdateView, self).get_form_kwargs(*args, **kwargs)
        form_kwargs['user'] = self.request.user
        form_kwargs['is_update'] = True
        return form_kwargs

class ClassDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = SchoolClass
    required_permissions = ['coordination', ]
    permission_required = 'classes.delete_schoolclass'
    success_message = "Turma removida com sucesso!"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(ClassDeleteView, self).delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('classes:classes_list')


class SchoolClassPublicList(generics.ListAPIView):
    queryset = SchoolClass.objects.all()
    serializer_class = SchoolClassSerializer
    filterset_fields = ['grade']

    def get_queryset(self):
        queryset = SchoolClass.objects.filter(
            coordination__unity__client__pk=self.kwargs['client_id'],
            class_type=SchoolClass.PROBE,
            date__gte=datetime.now().date()
        )
        return queryset  


classes_list = ClassList.as_view()
classes_create = ClassCreateView.as_view()
classes_update = ClassUpdateView.as_view()
classes_delete = ClassDeleteView.as_view()

classes_list_api = SchoolClasseList.as_view()
classes_list_public_api = SchoolClassPublicList.as_view()

