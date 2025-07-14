from typing import Any
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models.query import QuerySet
from django.http import HttpResponseRedirect
from django.urls import reverse
from fiscallizeon.accounts.models import User
from fiscallizeon.core.utils import CheckHasPermission
from django.views.generic import CreateView, UpdateView, ListView, TemplateView, DeleteView, RedirectView
from fiscallizeon.clients.models import ExamPrintConfig, Partner, TeachingStage, EducationSystem
from fiscallizeon.exams.models import ClientCustomPage
from fiscallizeon.clients.forms import EducationSystemForm, PartnerForm
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages

from fiscallizeon.classes.models import SchoolClass

class ExamPrintConfigsListTemplateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    template_name = 'clients/print_defaults_list.html'
    required_permissions = ['coordination', ]
    permission_required = 'clients.view_examprintconfig'
    
class ExamPrintConfigsCreateTemplateView(LoginRequiredMixin, CheckHasPermission, CreateView):
    template_name = 'clients/print_defaults_create_update.html'
    required_permissions = ['coordination', ]
    permission_required = 'clients.add_examprintconfig'
    queryset = ExamPrintConfig.objects.all()
    fields = '__all__'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['exam_custom_pages'] = ClientCustomPage.objects.filter(
            client__in=self.request.user.get_clients_cache()
        ).distinct()
        
        return context
    
    
class ExamPrintConfigsUpdateTemplateView(LoginRequiredMixin, CheckHasPermission, UpdateView):
    template_name = 'clients/print_defaults_create_update.html'
    required_permissions = ['coordination', ]
    permission_required = 'clients.change_examprintconfig'
    queryset = ExamPrintConfig.objects.all()
    fields = '__all__'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(client__in=self.request.user.get_clients_cache(), is_default=True)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        context['exam_custom_pages'] = ClientCustomPage.objects.filter(
            client__in=self.request.user.get_clients_cache()
        ).distinct()
        
        return context
    

class TeachingStageListTemplateView(LoginRequiredMixin, CheckHasPermission, ListView):
    template_name = 'clients/teaching_stage_list.html'
    required_permissions = ['coordination', ]
    permission_required = 'clients.view_teachingstage'
    queryset = TeachingStage.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(client__in=self.request.user.get_clients_cache())
        
        return queryset
    
class TeachingStageCreateTemplateView(LoginRequiredMixin, CheckHasPermission, CreateView):
    template_name = 'clients/teaching_stage_create_update.html'
    required_permissions = ['coordination', ]
    permission_required = 'clients.add_teachingstage'
    queryset = TeachingStage.objects.all()
    fields = '__all__'
    
class TeachingStageUpdateTemplateView(LoginRequiredMixin, CheckHasPermission, UpdateView):
    template_name = 'clients/teaching_stage_create_update.html'
    required_permissions = ['coordination', ]
    permission_required = 'clients.change_teachingstage'
    queryset = TeachingStage.objects.all()
    fields = '__all__'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(client__in=self.request.user.get_clients_cache())
        return queryset
    
class EducationSystemListTemplateView(LoginRequiredMixin, CheckHasPermission, ListView):
    template_name = 'clients/education_system_list.html'
    required_permissions = ['coordination', ]
    permission_required = 'clients.view_educationsystem'
    queryset = EducationSystem.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(client__in=self.request.user.get_clients_cache())
        
        return queryset
    
class EducationSystemCreateTemplateView(LoginRequiredMixin, CheckHasPermission, CreateView):
    template_name = 'clients/education_system_create_update.html'
    required_permissions = ['coordination', ]
    permission_required = 'clients.add_educationsystem'
    queryset = EducationSystem.objects.all()
    form_class = EducationSystemForm
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs
    
class EducationSystemUpdateTemplateView(LoginRequiredMixin, CheckHasPermission, UpdateView):
    template_name = 'clients/education_system_create_update.html'
    required_permissions = ['coordination', ]
    permission_required = 'clients.change_educationsystem'
    queryset = EducationSystem.objects.all()
    form_class = EducationSystemForm
    
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(client__in=self.request.user.get_clients_cache())
        return queryset
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs
    
class PartnersListView(LoginRequiredMixin, CheckHasPermission, ListView):
    template_name = 'dashboard/members/partners_list.html'
    required_permissions = ['coordination', ]
    permission_required = 'clients.view_partner'
    queryset = Partner.objects.all()
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(client__in=self.request.user.get_clients_cache())

        return queryset
    
class PartnerCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    template_name = 'dashboard/members/partner_create_update.html'
    required_permissions = ['coordination', ]
    permission_required = 'clients.add_partner'
    queryset = Partner.objects.all()
    model = Partner
    form_class = PartnerForm
    success_message = "Parceiro criado com sucesso"

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super().get_form_kwargs(*args, **kwargs)
        form_kwargs['request'] = self.request
        form_kwargs['is_update'] = False
        return form_kwargs

    def form_valid(self, form: PartnerForm):
        form.instance.client = self.request.user.get_clients()[0]    
        form.save()
                    
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('clients:partners_list')

class PartnerUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    template_name = 'dashboard/members/partner_create_update.html'
    model = Partner
    permission_required = 'clients.change_partner'
    form_class = PartnerForm
    success_message = 'Parceiro editado'

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super().get_form_kwargs(*args, **kwargs)
        form_kwargs['request'] = self.request
        form_kwargs['is_update'] = True
        return form_kwargs

    def get_success_url(self):
        return reverse('clients:partners_list')
    
    def form_valid(self, form: PartnerForm):

        if form.is_valid():
            if form.cleaned_data['username'] and form.cleaned_data['username'] != form.instance.user.username:
                form.instance.user.username = form.cleaned_data['username']
            if form.cleaned_data['password']:
                form.instance.user.set_password(form.cleaned_data['password'])

            form.save()
            form.instance.user.save()

            messages.success(self.request, self.success_message)
        return HttpResponseRedirect(self.get_success_url())
    
class PartnerDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = Partner
    required_permissions = ['coordination', ]
    permission_required = 'clients.delete_partner'
    success_message = "Parceiro removido!"

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, self.success_message)
        return super(PartnerDeleteView, self).delete(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('clients:partners_list')
    
class ConfigurationRedirectView(LoginRequiredMixin, CheckHasPermission, RedirectView):
    
    def get_redirect_url(self, *args, **kwargs):
        
        user = self.request.user
        
        if user.has_perm('clients.change_clientteacherobligationconfiguration'):
            return reverse('clients:obligation_teacher_configuration')
        
        elif user.has_perm('clients.change_clientquestionsconfiguration'):
            return reverse('clients:questions_configurations')
        
        elif user.has_perm('clients.change_confignotification'):
            return reverse('clients:config_notifications_create')
        
        elif user.client_has_integration and user.has_perm('integrations.view_integration'):
            return reverse('integrations:integration_create_update')
        
        return reverse('core:redirect_dashboard')