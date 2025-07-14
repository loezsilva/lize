from rest_framework import viewsets

from rest_framework.generics import ListAPIView
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework import generics
from fiscallizeon.clients.models import Client
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.subjects.serializers.main_topic import MainTopicSerializer, MainTopicSimpleSerializer
from fiscallizeon.subjects.models import MainTopic

class MainTopicViewSet(viewsets.ModelViewSet):
	serializer_class = MainTopicSerializer
	queryset = MainTopic.objects.all()

class MainTopicListApiView(LoginRequiredMixin, CheckHasPermission, ListAPIView):
    serializer_class = MainTopicSimpleSerializer
    queryset = MainTopic.objects.all()
    filterset_fields = ['id',  'name']
    required_permissions = [settings.COORDINATION, settings.TEACHER]

    def get_queryset(self):
        theme_id = self.request.query_params.get('theme_pk')
        if theme_id:
            queryset = MainTopic.objects.filter(theme_id=theme_id)
        else:
            queryset = MainTopic.objects.all()
        return queryset
    

class MainTopicApiCreateView(LoginRequiredMixin, CheckHasPermission, generics.CreateAPIView):
    queryset = MainTopic.objects.all()
    serializer_class = MainTopicSimpleSerializer
    required_permissions = [settings.COORDINATION, settings.TEACHER]

    def perform_create(self, serializer):
        serializer.validated_data['client'] = Client.objects.get(pk=self.request.user.get_clients_cache()[0])
        serializer.validated_data['created_by'] = self.request.user
        instance = serializer.save()
        return instance

main_topic_list_api = MainTopicListApiView.as_view()
main_topic_create_api = MainTopicApiCreateView.as_view()