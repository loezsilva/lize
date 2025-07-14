from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin

from rest_framework import generics, status
from rest_framework.response import Response

from fiscallizeon.clients.models import Client
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.subjects.models import Topic
from fiscallizeon.subjects.serializers.topics import TopicSimpleSerializer, TopicValidateSerializer


class TopicsCreateApiView(LoginRequiredMixin, CheckHasPermission, generics.CreateAPIView):
    model = Topic
    serializer_class = TopicValidateSerializer
    required_permissions = [settings.COORDINATION, settings.TEACHER]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.validated_data['client'] = Client.objects.get(pk=request.user.get_clients_cache()[0])
        serializer.validated_data['created_by'] = request.user
        instance = serializer.save()

        response_serializer = TopicSimpleSerializer(instance)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)
