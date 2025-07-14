from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import BasicAuthentication 

from celery.result import AsyncResult

from fiscallizeon.core.api import CsrfExemptSessionAuthentication

class ExamsExportResultsTaskStatusView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def get(self, request, export_id):
        result = AsyncResult(f'EXAMS_EXPORT_RESULTS_{export_id}')
        task_status = {
            'status': result.status,
            'details': result.info,
        }
        return Response(task_status)

exams_export_results = ExamsExportResultsTaskStatusView.as_view()