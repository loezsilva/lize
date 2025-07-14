import json

from rest_framework import status
from rest_framework.authentication import BasicAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from celery import states
from celery.result import AsyncResult

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin

from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.core.api import CsrfExemptSessionAuthentication

class GetGenericTaskStatusAPIWiew(LoginRequiredMixin, CheckHasPermission, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    required_permissions = [settings.COORDINATION, settings.STUDENT]

    def get_task_status(self, task_id):
        if not task_id:
            return {}

        result = AsyncResult(task_id)

        task_metadata = result.info
        try:
            if 'pid' in result.info or 'hostname' in result.info:
                task_metadata = {}
        except Exception as e:
            print(e)
            pass

        return {
            'status': result.status,
            'details': str(task_metadata),
        }

    def get(self, request):
        if not (task_id := request.GET.get('task_id')):
            return Response(
                status=status.HTTP_404_NOT_FOUND,
            )

        status_list = []
        if len(request.GET.getlist('task_id')) > 1:
            for task_id in request.GET.getlist('task_id'):
                status_list.append(True) if self.get_task_status(task_id).status == 'SUCCESS' else status_list.append(True)
            
            return Response(
                status=status.HTTP_200_OK,
                data={
                    "status": "SUCCESS" if not False in status_list else "FAILURE",
                    "details": ""
                }
            )
            
        task_status = self.get_task_status(task_id)
        return Response(
            status=status.HTTP_200_OK,
            data=task_status,
        )

get_generic_task_status = GetGenericTaskStatusAPIWiew.as_view()