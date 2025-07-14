from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response 

from celery.states import PENDING, STARTED, SUCCESS, FAILURE
from celery.result import AsyncResult

from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.notifications.models import Notification

class ExamCopyIATaskStatusView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def get(self, request):
        exam_id = self.request.GET.get('pk')
        export_verion = self.request.GET.get('export_version', '').strip()
        
        result = AsyncResult(f'AI_QUESTION_COPY_{exam_id}_{export_verion}')
        
        task_status = PENDING
        if result.status == STARTED:
            task_status = STARTED
            result.forget()
        elif result.status == SUCCESS:
            task_status = SUCCESS

            localhost_base_url = "http://localhost:8000/"
            staging_base_url = "https://staging.lizeedu.com.br/"
            production_base_url = "https://app.lizeedu.com.br/"
            urls = (
                f"{localhost_base_url}provas/?category=exam, "
                f"{staging_base_url}provas/?category=exam, "
                f"{production_base_url}provas/?category=exam, "
            )
            title = "Cópia realizada com sucesso!"
            description = "A cópia foi gerada com sucesso utilizando IA."
            Notification.create_single_notification_for_user(urls, title, description, self.request.user)
            result.forget()

        elif result.status == FAILURE:
            task_status = FAILURE
            result.forget()

        return Response(
            status=status.HTTP_200_OK,
            data={
                'status': task_status,
            },
        )


exam_copy_ia_task_status = ExamCopyIATaskStatusView.as_view()