from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from celery.states import PENDING, STARTED, SUCCESS, FAILURE
from celery.result import AsyncResult

from fiscallizeon.core.api.csrf_exempt_session import CsrfExemptSessionAuthentication
from fiscallizeon.omrnps.serializers.nps_application import NPSApplicationIDSerializer
from fiscallizeon.omrnps.models import NPSApplication
from fiscallizeon.omrnps.tasks.export.export_application_files import export_application_files
from fiscallizeon.core.templatetags.cdn_url import cdn_url

class ExportApplicationBagApiView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def post(self, request, format=None):
        serializer = NPSApplicationIDSerializer(data=request.data)
        if serializer.is_valid():
            nps_application = NPSApplication.objects.get(pk=serializer.data['nps_application_id'])
            nps_application.export_count += 1
            nps_application.sheet_exporting_status = NPSApplication.EXPORTING
            nps_application.save()
            
            task_id = f'EXPORT_NPS_BAG_{str(nps_application.pk)}_{nps_application.export_count}'
            export_application_files.apply_async(args=[
                    serializer.data['nps_application_id'],
                    nps_application.export_count
                ],
                task_id=task_id,
            )
            return Response({"task_id": task_id})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ExportNPSApplicationBagStatusApiView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def get(self, request):
        pk = self.request.GET.get('id')
        export_version = self.request.GET.get('version')
        result = AsyncResult(f'EXPORT_NPS_BAG_{pk}_{export_version}')
        result_merge = AsyncResult(f'GROUP_FILES_NPS_APPLICATION_{pk}_{export_version}')
        
        answer_sheet = None
        last_answer_sheet_generation = None

        percent = 0
        if result.children:
            total_tasks = len(list(result.children[0]))
            pending_tasks = len(list(filter(lambda x: x.status == PENDING, list(result.children[0]))))
            percent = (total_tasks - pending_tasks) / total_tasks

        task_status = PENDING
        if result.status == SUCCESS and percent < 1:
            task_status = STARTED

        elif result.status == SUCCESS and result_merge.status in [PENDING, STARTED]:
            task_status = STARTED

        elif result_merge.status == SUCCESS:
            task_status = SUCCESS
            nps_application = NPSApplication.objects.using('default').get(pk=pk)
            answer_sheet = nps_application.answer_sheet.url if nps_application.answer_sheet else ''
            last_answer_sheet_generation = nps_application.last_answer_sheet_generation
            result.forget()

        elif FAILURE in [result.status, result_merge.status]:
            task_status = FAILURE
            result.forget()

        return Response(
            status=status.HTTP_200_OK,
            data={
                'status': task_status,
                'percent': percent,
                'application': {
                    'answer_sheet': answer_sheet,
                    'last_answer_sheet_generation': last_answer_sheet_generation,
                }
            },
        )
