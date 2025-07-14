from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import BasicAuthentication 

from celery import states
from celery.result import AsyncResult

from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.exams.models import Exam
from fiscallizeon.exams.tasks import export_exam_attachments
from fiscallizeon.core.utils import CheckHasPermission

class ExamExportAttachmentsView(APIView, CheckHasPermission):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    required_permissions = ['coordination', ]

    def get(self, request, pk, task_id):
        result = AsyncResult(f'EXPORT_EXAM_ATTACHMENTS_{str(pk)}_{task_id}')

        if result.info:
            return Response(status=status.HTTP_200_OK)

        export_exam_attachments.apply_async(
            args=[str(pk)],
            task_id=f'EXPORT_EXAM_ATTACHMENTS_{str(pk)}_{task_id}'
        )
        return Response(status=status.HTTP_200_OK)

class ExamExportAttachmentsStatusView(APIView, CheckHasPermission):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    required_permissions = ['coordination', ]

    def get(self, request, pk, task_id):
        exam = Exam.objects.get(pk=pk)
        result = AsyncResult(f'EXPORT_EXAM_ATTACHMENTS_{exam.pk}_{task_id}')

        if result.status == states.FAILURE:
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        task_status = {
            'status': result.status,
            'details': str(result.info) if result.info else None       
        }
        return Response(task_status, status=status.HTTP_200_OK)


exam_export_attachments = ExamExportAttachmentsView.as_view()
exam_export_attachments_status = ExamExportAttachmentsStatusView.as_view()