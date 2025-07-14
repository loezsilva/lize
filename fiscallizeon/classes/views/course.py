
from django.urls import reverse

from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages

from fiscallizeon.classes.models import Course
from fiscallizeon.classes.forms import CourseForm
from fiscallizeon.core.utils import CheckHasPermission

from django.contrib.auth.mixins import LoginRequiredMixin

class CourseList(LoginRequiredMixin, CheckHasPermission, ListView):
    model = Course
    required_permissions = ['coordination', ]
    permission_required = 'classes.view_course'
    paginate_by = 20
    template_name = "dashboard/courses/course_list.html"
    
    def get_queryset(self):
        queryset = super(CourseList, self).get_queryset()
        
        queryset = Course.objects.filter(
            client__in=self.request.user.get_clients_cache()
        ).order_by("name")
        
        if self.request.GET.get('q_name', ""):
            queryset = queryset.filter(
                name__icontains=self.request.GET.get('q_name', "")
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super(CourseList, self).get_context_data(**kwargs)
        
        context['q_name'] = self.request.GET.get('q_name', "")

        list_filters = [context['q_name']]
        context['count_filters'] = len(list_filters) - list_filters.count("")

        return context
class CourseCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    model = Course
    required_permissions = ['coordination', ]
    permission_required = 'classes.add_course'
    form_class = CourseForm
    template_name = "dashboard/courses/course_create_update.html"
    success_message = "Tipo de curso cadastrado com sucesso!"

    def get_success_url(self):
        return reverse('classes:courses_list')
    
    def form_valid(self, form):
        form.save(commit=False)
        form.instance.client=self.request.user.get_clients().first()
        
        return super(CourseCreateView, self).form_valid(form)
        

class CourseUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    model = Course
    required_permissions = ['coordination', ]
    permission_required = 'classes.change_course'
    form_class = CourseForm
    template_name = "dashboard/courses/course_create_update.html"
    success_message = "Tipo de curso atualizado com sucesso!"

    def get_success_url(self):
        return reverse('classes:courses_list')
    
    def form_valid(self, form):
        form.save(commit=False)
        form.instance.client=self.request.user.get_clients().first()
        
        return super(CourseUpdateView, self).form_valid(form)
        
    
class CourseDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = Course
    required_permissions = ['coordination', ]
    permission_required = 'classes.delete_course'
    success_message = "Tipo de Curso removido com sucesso!"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(CourseDeleteView, self).delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('classes:courses_list') 

courses_list = CourseList.as_view()
courses_create = CourseCreateView.as_view()
courses_update = CourseUpdateView.as_view()
courses_delete = CourseDeleteView.as_view()