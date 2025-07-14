from fiscallizeon.classes.models import Grade
from django.urls import reverse
from django.conf import settings
from django.contrib import messages
from django.http.response import HttpResponseRedirect


from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from django.db.models import Q

from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.diagramations.forms import DiagramationRequestForm
from fiscallizeon.diagramations.models import DiagramationRequest


class DiagramationRequestListView(LoginRequiredMixin, CheckHasPermission, ListView):
    template_name = 'dashboard/diagramation_request/diagramation_request_list.html'
    required_permissions = [settings.COORDINATION, ]
    model = DiagramationRequest
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_diagramation:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super(DiagramationRequestListView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DiagramationRequestListView, self).get_context_data(**kwargs)
        context['q'] = self.request.GET.get("q", "")
        
        context['q_application_date'] = self.request.GET.get("q_application_date", "")
        context['q_status'] = self.request.GET.get("q_status", "")
        context['q_grades'] = self.request.GET.getlist('q_grades', "")

        context["grades"] = Grade.objects.all()
        
        list_filters = [context['q_application_date'], context['q_status']]

        context['count_filters'] = len(list_filters) - list_filters.count("")

        return context

    def get_queryset(self, **kwargs):

        queryset = DiagramationRequest.objects.filter(
            Q(created_by=self.request.user) |
            Q(created_by__coordination_member__coordination__in=self.request.user.get_coordinations_cache())
        ).distinct().order_by('application_date')

        if self.request.GET.get("q_application_date"):
            queryset = queryset.filter(application_date=self.request.GET.get("q_application_date"))

        if self.request.GET.get("q_status"):
            queryset = queryset.filter(status=self.request.GET.get("q_status"))
        
        if self.request.GET.getlist('q_grades'):
            queryset = queryset.filter(
                grade__pk__in=self.request.GET.getlist('q_grades')
            )

        return queryset


class DiagramationRequestCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    template_name = "dashboard/diagramation_request/diagramation_request_create_update.html"
    model = DiagramationRequest
    form_class = DiagramationRequestForm
    required_permissions = [settings.COORDINATION, ]
    success_message = "Solicitação de diagramação enviada com sucesso"

    def dispatch(self, request, *args, **kwargs):
        if request.user and not request.user.is_anonymous and not request.user.client_has_diagramation:
            messages.warning(request, 'Cliente não possui este módulo')
            return HttpResponseRedirect(reverse('core:redirect_dashboard'))

        return super(DiagramationRequestCreateView, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(DiagramationRequestCreateView, self).get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs

    def form_valid(self, form):
        if form.is_valid():
            self.object = form.save(commit=False)
            self.object.created_by = self.request.user
            self.object.save()
            form.save_m2m()

            return HttpResponseRedirect(self.get_success_url())
        else:
            return self.render_to_response(self.get_context_data(form=form))

    def get_success_url(self):
        return reverse('diagramations:diagramation_request_list')


class DiagramationRequestUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    template_name = "dashboard/diagramation_request/diagramation_request_create_update.html"
    model = DiagramationRequest
    form_class = DiagramationRequestForm
    required_permissions = [settings.COORDINATION, ]
    success_message = "Solicitação de diagramação atualizada com sucesso"

    def get_form_kwargs(self):
        kwargs = super(DiagramationRequestUpdateView, self).get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs

    def get_success_url(self):
        return reverse('diagramations:diagramation_request_list')


class DiagramationRequestDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = DiagramationRequest
    required_permissions = [settings.COORDINATION, ]
    success_message = "Solicitação de diagramação removida com sucesso!"

    def get_success_url(self):
        return reverse('diagramations:diagramation_request_list')


diagramation_request_list = DiagramationRequestListView.as_view()
diagramation_request_create = DiagramationRequestCreateView.as_view()
diagramation_request_update = DiagramationRequestUpdateView.as_view()
diagramation_request_delete = DiagramationRequestDeleteView.as_view()

