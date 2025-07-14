from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import redirect

from django.db.models import Q, Exists, OuterRef
from django.utils import timezone

from django.conf import settings
from django.views.generic import ListView
from fiscallizeon.classes.models import Grade
from django.views.generic.base import TemplateView
from fiscallizeon.core.utils import CheckHasPermission
from django.contrib.auth.mixins import LoginRequiredMixin
from fiscallizeon.integrations.forms import IntegrationForm
from fiscallizeon.integrations.models import Integration
from django.urls import reverse

from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.subjects.models import Subject


class IntegrationCreateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    required_permissions = [settings.COORDINATION]
    template_name = 'integrations/token_create_update.html'
    permission_required = 'integrations.view_integration'

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_integration:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))
        return super(IntegrationCreateView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
                
        client = self.request.user.get_clients().first()

        if hasattr(client, 'integration'):
            old_token = client.integration.token
            form = IntegrationForm(instance=client.integration, data=self.request.POST)
            if form.is_valid():
                integration = form.save(commit=False)
                if not integration.token:
                    integration.token = old_token
                integration.save()
            else:
                if form.errors.get('school_code'):
                    messages.error(request, "Para integração com o Ischolar você precisa do código da escola")
                else:
                    messages.error(request, "Preencha os campos corretamente e tente novamente")
        else:
            form = IntegrationForm(self.request.POST)
            if form.is_valid():
                integration = form.save(commit=False)
                client = client
                integration.client = client
                integration.save()
                client.save()
                messages.success(request, "Chave adicionada ou alterada com sucesso!")
            else:
                if form.errors.get('school_code'):
                    messages.error(request, "Para integração com o Ischolar você precisa do código da escola")
                else:
                    messages.error(request, "Preencha os campos corretamente e tente novamente")
            
        return redirect(reverse('integrations:integration_create_update'))
    
    def get_context_data(self, **kwargs):
        context = super(IntegrationCreateView, self).get_context_data(**kwargs)
        
        context['form'] = IntegrationForm()
        
        client = self.request.user.get_clients().first()
        
        if hasattr(client, 'integration'):
            context['fake_token'] = client.integration.token[:4] + '****' if client.integration.token else '****'
            context['form'] = IntegrationForm(instance=client.integration)

        return context
        
class IntegrationsSynconizationsTemplateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    required_permissions = [settings.COORDINATION]
    permission_required = 'integrations.view_integration'
    current_token = None
    integration_token = None
    integration = None
    
    def get_template_names(self):
        user = self.request.user
        return [f"integrations/{self.integration.get_erp_display().lower()}_syncronizations.html"]

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if user.is_authenticated:
            if not hasattr(user, 'client'):
                messages.warning(request, "Seu usuário não possui um cliente associado.")
                return redirect("core:redirect_dashboard")

            client = user.client

            integration = getattr(client, 'integration', None)
            if not integration:
                messages.warning(request, "Cliente não possui integração configurada.")
                return redirect("core:redirect_dashboard")

            self.integration = integration

            if not user.client_has_integration:
                messages.warning(request, 'Cliente não possui este módulo')
                return redirect('core:redirect_dashboard')

            if not user.client_has_access_token:
                messages.warning(request, "Você não tem token cadastrado, cadastre uma chave token para acessar a página solicitada.")
                return redirect("integrations:integration_create_update")

            if self.integration.erp == Integration.ACTIVESOFT:
                token_index = self.kwargs.get('token')
                if token_index is not None:
                    try:
                        self.integration_token = self.integration.tokens.all()[int(token_index)]
                    except (IndexError, ValueError):
                        messages.error(request, "Token inválido.")
                        return redirect('core:redirect_dashboard')
                else:
                    self.integration_token = self.integration.tokens.order_by('created_at').first()

                if self.integration_token:
                    self.current_token = self.integration_token.token
                else:
                    messages.error(request, "Nenhum token disponível para esta integração.")
                    return redirect('core:redirect_dashboard')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        user = self.request.user
        context = super(IntegrationsSynconizationsTemplateView, self).get_context_data(**kwargs)
        context['grades'] = Grade.objects.all().exclude(name__icontains="concurso")
        
        classes = SchoolClass.objects.filter(
            coordination__unity__client__in=self.request.user.get_clients_cache(),
            id_erp__isnull=False,
            school_year=timezone.now().year
        ).distinct().order_by('name')
        
        context['token_index'] = self.kwargs.get('token', 0)
        context['integration_token'] = self.integration_token
        context['token'] = self.current_token
        
        if self.integration_token:
            context['token_expirated'] = self.integration_token.expiration_date and self.integration_token.expiration_date < timezone.now().date()
        
        context['headers'] = user.client.integration.headers(token=self.current_token if self.current_token else None)
        
        context['syncronized_classes'] = classes.distinct()
        return context


class SubjectCodeTemplateView(LoginRequiredMixin, CheckHasPermission, ListView):
    model = Subject
    required_permissions = [settings.COORDINATION, ]
    permission_required = 'subjects.view_topic'
    template_name = "integrations/subjects/subject_code_list_create.html"
    paginate_by = 20

    def get_queryset(self):
        queryset = super(SubjectCodeTemplateView, self).get_queryset()
        queryset = Subject.objects.filter(
            Q(parent_subject__isnull=True) |
            Q(client__isnull=True) |
            Q(
                Q(parent_subject__isnull=False) &
                Q(client__in=self.request.user.get_clients_cache())
            )
        )

        if self.request.user.get_clients().first().use_only_own_subjects:
            queryset = queryset.filter(
                client__in=self.request.user.get_clients_cache()
            )

        return queryset
    
    def get_context_data(self, **kwargs):
        context = super(SubjectCodeTemplateView, self).get_context_data(**kwargs)
        return context

class IntegrationNotesTemplateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    permission_required = 'integrations.view_integration'
    current_token = None
    integration_token = None
    
    def get_template_names(self):
        user = self.request.user
        integration = user.client.integration
        return [f"integrations/{integration.get_erp_display().lower()}_notes_integration.html"]
    
    def dispatch(self, request, *args, **kwargs):
        user = request.user

        if not user.is_authenticated:
            return self.handle_no_permission()

        integration = user.client.integration
        
        if user and not user.is_anonymous and not user.client_has_integration:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        if not user.client_has_access_token:
            messages.warning(request, "Você não tem token cadastrado, cadastre uma chave token para acessar a página solicitada.")
            return redirect("integrations:integration_create_update")
        
        if integration.erp == Integration.ACTIVESOFT:
            
            if token_index := self.kwargs.get('token'):
                self.integration_token = integration.tokens.all()[token_index]
                self.current_token = self.integration_token.token
            else:
                self.integration_token = integration.tokens.order_by('created_at').first()
                self.current_token = self.integration_token.token
            
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        user = self.request.user
        
        context["grades"] = Grade.objects.all().order_by('level')
        
        context['token_index'] = self.kwargs.get('token', 0)
        context['integration_token'] = self.integration_token
        context['token'] = self.current_token
        if self.integration_token:
            context['token_expirated'] = self.integration_token.expiration_date and self.integration_token.expiration_date < timezone.now().date()
        
        context['headers'] = user.client.integration.headers(token=self.current_token if self.current_token else None)
        
        return context