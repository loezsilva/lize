from django.utils import timezone
from django.conf import settings
from rest_framework.generics import CreateAPIView, UpdateAPIView

from fiscallizeon.events.serializers import events
from fiscallizeon.events.models import Event
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.core.api import CsrfExemptSessionAuthentication

from rest_framework.authentication import BasicAuthentication 

class CreateEventView(CreateAPIView):
    required_permissions = [settings.COORDINATION, settings.INSPECTOR, settings.STUDENT, settings.TEACHER, ]
    serializer_class = events.CreateEventSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )


class UpdateEventView(UpdateAPIView):
    queryset = Event.objects.all()
    required_permissions = [settings.COORDINATION, settings.INSPECTOR, settings.TEACHER]
    serializer_class = events.UpdateEventSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def perform_update(self, serializer):
        serializer.save(
            inspector=self.request.user,
            response_datetime=timezone.now().astimezone(),
            start=timezone.now().astimezone(),
            end=None
        )
        
class FinishEventView(UpdateAPIView):
    queryset = Event.objects.all()
    required_permissions = [settings.STUDENT]
    serializer_class = events.FinishEventSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def perform_update(self, serializer):
        serializer.save(
            end=timezone.now().astimezone()
        )


event_create = CreateEventView.as_view()
event_update = UpdateEventView.as_view()
event_finish = FinishEventView.as_view()
