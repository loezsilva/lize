from django.utils import timezone
from django.http.response import JsonResponse

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication

from fiscallizeon.integrations.models import Integration
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.integrations.tasks.export_exams_realms import export_exams_realms

class SyncExam(APIView):
    render_classes = JsonResponse
    authentication_classes = [CsrfExemptSessionAuthentication, TokenAuthentication]

    def post(self, request):
        data = request.data
        client = self.request.user.get_clients()[0]

        integration = Integration.objects.filter(
            client=client,
            erp=Integration.REALMS,
        ).first()

        if not integration:
            return Response("Cliente não possui integração realms", status=401)

        if not data:
            return Response("É necessário informar pelo menos um caderno para sincronização", status=400)

        unix_time = int(timezone.now().timestamp())
        task_id = f'EXPORT_EXAMS_REALMS_{unix_time}'
        export_exams_realms.apply_async(args=(data, client.pk,), task_id=task_id)
        return Response({'task_id': task_id})