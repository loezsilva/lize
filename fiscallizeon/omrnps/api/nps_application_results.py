import uuid
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from celery.result import AsyncResult

from fiscallizeon.core.api.csrf_exempt_session import CsrfExemptSessionAuthentication
from fiscallizeon.omrnps.tasks.results.export_results import export_application_results

class ExportNPSApplicationResultsApiView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def post(self, request, format=None):
        nps_applications = sorted(request.data.get('nps_applications'), key=lambda x: x['id'])
        applications_ids = []
        short_ids = ''
        versions = ''
        
        for application in nps_applications:
            applications_ids.append(application['id'])
            versions += str(application['export_version'])
            short_ids += str(application['id'][:5])
            
        task_id = f'EXPORT_NPS_APPLICATION_DATA_{short_ids}_{versions}'

        export_application_results.apply_async(
            kwargs={
                'nps_applications_ids': applications_ids
            },
            task_id=task_id,
        )
        return Response({'task_id': task_id})


class ExportNPSApplicationResultsStatusApiView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def post(self, request):
        nps_applications = sorted(request.data.get('nps_applications'), key=lambda x: x['id'])
        applications_ids = []
        short_ids = ''
        versions = ''
        
        for application in nps_applications:
            applications_ids.append(application['id'])
            versions += str(application['export_version'])
            short_ids += str(application['id'][:5])
            
        task_id = f'EXPORT_NPS_APPLICATION_DATA_{short_ids}_{versions}'
        
        result = AsyncResult(task_id)

        return Response(
            status=status.HTTP_200_OK,
            data={
                'status': result.status,
                'result_file_url': result.info,
            },
        )


class NPSApplicationExportResultsTaskStatusView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def get(self, request, export_id):
        result = AsyncResult(f'EXPORT_NPS_APPLICATION_DATA_{export_id}')
        task_status = {
            'status': result.status,
            'details': repr(result.info) if result.status != 'SUCCESS' else result.info,
        }
        return Response(task_status)
