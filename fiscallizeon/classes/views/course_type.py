
from django.urls import reverse

from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages

from fiscallizeon.classes.models import CourseType
from fiscallizeon.classes.forms import CourseTypeForm
from fiscallizeon.core.utils import CheckHasPermission

from django.contrib.auth.mixins import LoginRequiredMixin

class CourseTypeList(LoginRequiredMixin, CheckHasPermission, ListView):
    model = CourseType
    required_permissions = ['coordination', ]
    permission_required = 'classes.view_coursetype'
    paginate_by = 20
    template_name = "dashboard/courses_type/course_type_list.html"
    
    def get_queryset(self):
        queryset = super(CourseTypeList, self).get_queryset()
        
        queryset = CourseType.objects.filter(
            client__in=self.request.user.get_clients_cache()
        ).order_by("name")
        
        if self.request.GET.get('q_name', ""):
            queryset = queryset.filter(
                name__icontains=self.request.GET.get('q_name', "")
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super(CourseTypeList, self).get_context_data(**kwargs)
        
        context['q_name'] = self.request.GET.get('q_name', "")

        list_filters = [context['q_name']]
        context['count_filters'] = len(list_filters) - list_filters.count("")

        return context
class CourseTypeCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    model = CourseType
    required_permissions = ['coordination', ]
    permission_required = 'classes.add_coursetype'
    form_class = CourseTypeForm
    template_name = "dashboard/courses_type/course_type_create_update.html"
    success_message = "Tipo de curso cadastrado com sucesso!"

    def get_success_url(self):
        return reverse('classes:courses_type_list')
    
    def form_valid(self, form):
        form.save(commit=False)
        form.instance.client=self.request.user.get_clients().first()
        
        return super(CourseTypeCreateView, self).form_valid(form)
        

class CourseTypeUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    model = CourseType
    required_permissions = ['coordination', ]
    permission_required = 'classes.change_coursetype'
    form_class = CourseTypeForm
    template_name = "dashboard/courses_type/course_type_create_update.html"
    success_message = "Tipo de curso atualizado com sucesso!"

    def get_success_url(self):
        return reverse('classes:courses_type_list')
    
    def form_valid(self, form):
        form.save(commit=False)
        form.instance.client=self.request.user.get_clients().first()
        
        return super(CourseTypeUpdateView, self).form_valid(form)
        
    
class CourseTypeDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = CourseType
    required_permissions = ['coordination', ]
    permission_required = 'classes.delete_coursetype'
    success_message = "Tipo de Curso removido com sucesso!"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(CourseTypeDeleteView, self).delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('classes:courses_type_list') 

courses_type_list = CourseTypeList.as_view()
courses_type_create = CourseTypeCreateView.as_view()
courses_type_update = CourseTypeUpdateView.as_view()
courses_type_delete = CourseTypeDeleteView.as_view()