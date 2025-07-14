from rest_framework import viewsets
from django.conf import settings

from rest_framework.generics import ListAPIView, CreateAPIView
from django.views.generic.edit import CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework import generics
from fiscallizeon.clients.models import Client
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.subjects.forms.theme import ThemeForm
from fiscallizeon.subjects.serializers.theme import ThemeSerializer, ThemeSimpleSerializer
from fiscallizeon.subjects.models import Theme
class ThemeViewSet(viewsets.ModelViewSet):
	serializer_class = ThemeSerializer
	queryset = Theme.objects.all()

class ThemeListApiView(ListAPIView):
    serializer_class = ThemeSimpleSerializer
    queryset = Theme.objects.all()
    filterset_fields = ['id',  'name']
    

class ThemeCreateApiView(LoginRequiredMixin, CheckHasPermission, CreateAPIView):
    required_permissions = [settings.COORDINATION, settings.TEACHER]

    queryset = Theme.objects.all()
    serializer_class = ThemeSimpleSerializer

    def perform_create(self, serializer):
        serializer.validated_data['client'] = Client.objects.get(pk=self.request.user.get_clients_cache()[0])
        serializer.validated_data['created_by'] = self.request.user
        instance = serializer.save()
        return instance
    
theme_list_api = ThemeListApiView.as_view()
theme_create_api = ThemeCreateApiView.as_view()