from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.http.response import HttpResponseRedirect
from django.urls import reverse
from django.contrib import messages
from django.views.generic import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from rest_framework import generics
from django_filters import rest_framework as filters_restframework

from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.inspectors.serializers.inspectors import InspectorSimpleSerializer
from fiscallizeon.inspectors.forms import InspectorForm
from fiscallizeon.core.utils import CheckHasPermission
from rest_framework.filters import SearchFilter

from django.contrib.auth.mixins import LoginRequiredMixin

from fiscallizeon.notifications.models import Notification
from fiscallizeon.notifications.functions import get_and_create_notifications



class InspectorList(LoginRequiredMixin, CheckHasPermission,  ListView):
    model = Inspector
    permission_required = 'inspectors.view_inspector'
    required_permissions = ['coordination', ]
    paginate_by = 30
    template_name = "dashboard/inspectors/inspector_list.html"
    nps_app_label = 'Inspector'

    def get_queryset(self):
        queryset = Inspector.objects.filter(
            Q(
                inspector_type=Inspector.INSPECTOR,
				coordinations__unity__client__in=self.request.user.get_clients_cache()
			)
        ).distinct()

        queryset = queryset.filter(
            user__is_active=True
        )

        return queryset


class InspectorCreateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, CreateView):
    model = Inspector
    required_permissions = ['coordination', ]
    permission_required = 'inspectors.add_inspector'
    form_class = InspectorForm
    template_name = "dashboard/inspectors/inspector_create_update.html"
    success_message = "Fiscal cadastrado com sucesso!"
    nps_app_label = 'Inspector'

    def get_form_kwargs(self):
        kwargs = super(InspectorCreateView, self).get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs

    def get_success_url(self):
        
        get_and_create_notifications(view=self, trigger=Notification.AFTER_CREATE)
        
        return reverse('inspectors:inspectors_list')


class InspectorUpdateView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, UpdateView):
    model = Inspector
    required_permissions = ['coordination', ]
    permission_required = 'inspectors.change_inspector'
    form_class = InspectorForm
    template_name = "dashboard/inspectors/inspector_create_update.html"
    success_message = "Fiscal atualizado com sucesso!"
    nps_app_label = 'Inspector'

    def get_form_kwargs(self):
        kwargs = super(InspectorUpdateView, self).get_form_kwargs()
        kwargs.update({'user' : self.request.user})
        return kwargs

    def get_success_url(self):
        
        get_and_create_notifications(view=self, trigger=Notification.AFTER_UPDATE)
        
        return reverse('inspectors:inspectors_list')


class InspectorDeleteView(LoginRequiredMixin, CheckHasPermission, SuccessMessageMixin, DeleteView):
    model = Inspector
    required_permissions = ['coordination', ]
    permission_required = 'inspectors.delete_inspector'
    success_message = "Fiscal removido com sucesso!"
    nps_app_label = 'Inspector'

    def form_valid(self, form):
        try:
            self.object.delete()
            
            get_and_create_notifications(view=self, trigger=Notification.AFTER_DELETE)
            
            messages.success(self.request, self.success_message)
            
        except ProtectedError:
            messages.error(self.request, "Ocorreu um erro ao remover, o fiscal tem disciplinas ou coordenações adicionadas.")
            
        return HttpResponseRedirect(self.get_success_url())  

    def get_success_url(self):
        return self.request.META.get('HTTP_REFERER', None)


class InspectorsApiList(LoginRequiredMixin, CheckHasPermission, generics.ListCreateAPIView):
    queryset = Inspector.objects.all()
    required_permissions = ['coordination', ]
    serializer_class = InspectorSimpleSerializer
    filter_backends = [SearchFilter, filters_restframework.DjangoFilterBackend]
    search_fields = ['name']
    filterset_fields = {
        'id': ['in', 'exact'],
        'coordinations__unity': ['in', 'exact'],
    }

    def get_queryset(self):
        queryset = Inspector.objects.filter(
            Q(
                Q(coordinations__unity__client__in=self.request.user.get_clients_cache()) |
                Q(coordinations__isnull=True)
            ) &
            Q(
                user__is_active=True
            )
        ).distinct()

        return queryset


inspectors_list = InspectorList.as_view()
inspectors_create = InspectorCreateView.as_view()
inspectors_update = InspectorUpdateView.as_view()
inspectors_delete = InspectorDeleteView.as_view()
inspectors_list_api = InspectorsApiList.as_view()
