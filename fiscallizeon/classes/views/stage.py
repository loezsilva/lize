from django.urls import reverse

from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages

from fiscallizeon.classes.models import Stage
from fiscallizeon.classes.forms import StageForm
from fiscallizeon.core.utils import CheckHasPermission

from django.contrib.auth.mixins import LoginRequiredMixin

class StageList(LoginRequiredMixin, CheckHasPermission, ListView):
    model = Stage
    required_permissions = ['coordination', ]
    permission_required = 'classes.view_stage'
    paginate_by = 20
    template_name = "dashboard/stages/stage_list.html"
    
    def get_queryset(self):
        queryset = super(StageList, self).get_queryset()
        
        if self.request.GET.get('q_name', ""):
            queryset = queryset.filter(
                name__icontains=self.request.GET.get('q_name', "")
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super(StageList, self).get_context_data(**kwargs)
        
        context['q_name'] = self.request.GET.get('q_name', "")

        list_filters = [context['q_name']]
        context['count_filters'] = len(list_filters) - list_filters.count("")

        return context
    
class StageCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    model = Stage
    required_permissions = ['coordination', ]
    permission_required = 'classes.add_stage'
    form_class = StageForm
    template_name = "dashboard/stages/stage_create_update.html"
    success_message = "Etapa cadastrada com sucesso!"

    def get_success_url(self):
        return reverse('classes:stage_list')
    
class StageUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    model = Stage
    required_permissions = ['coordination', ]
    permission_required = 'classes.change_stage'
    form_class = StageForm
    template_name = "dashboard/stages/stage_create_update.html"
    success_message = "Etapa atualizada com sucesso!"

    def get_success_url(self):
        return reverse('classes:stage_list')
class StageDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = Stage
    required_permissions = ['coordination', ]
    permission_required = 'classes.delete_stage'
    success_message = "Etapa removida com sucesso!"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(StageDeleteView, self).delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('classes:stage_list')
    
stage_list = StageList.as_view()
stage_create = StageCreateView.as_view()
stage_update = StageUpdateView.as_view()
stage_delete = StageDeleteView.as_view()