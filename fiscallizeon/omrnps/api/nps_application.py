from django.conf import settings

from rest_framework.views import APIView
from rest_framework.renderers import JSONRenderer
from rest_framework.response import Response
from rest_framework.generics import RetrieveAPIView

from django.contrib.auth.mixins import LoginRequiredMixin

from fiscallizeon.omrnps.models import NPSApplication
from fiscallizeon.omrnps.serializers.nps_application import NPSApplicationSerializer
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.core.api.csrf_exempt_session import CsrfExemptSessionAuthentication

class NPSApplicationApiListView(LoginRequiredMixin, CheckHasPermission, APIView):
    renderer_classes = [JSONRenderer]
    required_permissions = [settings.COORDINATION]
    def get(self, request, format=None):
        search = request.GET.get("search", "")

        applications = NPSApplication.objects.filter(
            name__icontains=search,
            client__in=self.request.user.get_clients_cache(),
        ).order_by('name')

        results = []
        for application in applications:
            results.append(
                {
                    "id": application.pk,
                    "name": application.name,
                },
            )

        return Response(results)


class NPSApplicationRetrieve(RetrieveAPIView):
    model = NPSApplication
    queryset = NPSApplication.objects.all()
    serializer_class = NPSApplicationSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )