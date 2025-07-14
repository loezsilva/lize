from rest_framework.views import APIView
from rest_framework.response import Response

from celery import states
from celery.result import AsyncResult

from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.omr.models import OMRUpload

class OMRUploadTaskStatusView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def get_number(self, result, status):
        if result and result.info:
            return result.info.get(status, 0)
        return 0

    def get(self, request, pk):
        try:
            result = AsyncResult(f'PROCESS_LIZE_SHEETS_{pk}')

            task_status = {
                'status': states.PENDING,
                'details': {'done': 0, 'total': 1}
            }

            if result.children:
                total_tasks = len(list(result.children[0]))
                done_tasks = len(list(filter(lambda x: x.status == states.SUCCESS, list(result.children[0]))))

                task_status = {
                    'status': states.STARTED if done_tasks != total_tasks else states.SUCCESS,
                    'details': {
                        'done': done_tasks,
                        'total': total_tasks,
                    }
                }
            else:
                task_status['status'] = states.SUCCESS if result.ready() else states.PENDING

            if task_status.get('status', '') == states.SUCCESS:
                omr_upload = OMRUpload.objects.get(pk=pk)
                task_status['total_pages'] = omr_upload.total_pages + omr_upload.total_errors_count
                task_status['error_pages'] = omr_upload.total_errors_count

            return Response(task_status)
        except Exception as e:
            return Response(f'Erro na obtenção dos dados {e}', status=500)


omr_upload_task_status = OMRUploadTaskStatusView.as_view()