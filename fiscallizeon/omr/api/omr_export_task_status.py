from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response 

from celery.states import PENDING, STARTED, SUCCESS, FAILURE
from celery.result import AsyncResult

from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.core.templatetags.cdn_url import cdn_url
from fiscallizeon.applications.models import Application

class OMRExportTaskStatusView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def get(self, request, pk, export_verion):
        result = AsyncResult(f'EXPORT_SHEETS_{pk}_{export_verion}')
        result_merge = AsyncResult(f'GROUP_FILES_APPLICATION_{pk}_{export_verion}')
        
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
            application = Application.objects.using('default').get(pk=pk)
            answer_sheet = cdn_url(application.answer_sheet.url) if application.answer_sheet else ''
            last_answer_sheet_generation = application.last_answer_sheet_generation
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


omr_export_task_status = OMRExportTaskStatusView.as_view()