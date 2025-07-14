from rest_framework.generics import RetrieveAPIView
from rest_framework.views import APIView
from rest_framework.response import Response

from celery import states
from celery.result import AsyncResult

from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.omrnps.models import OMRNPSUpload
from fiscallizeon.omrnps.serializers.omr_nps_upload import OMRNPSUploadStatusSerializer
from fiscallizeon.omrnps.permissions import IsOMRNPSUploadOwner
from rest_framework.permissions import IsAuthenticated


class OMRNPSUploadStatusView(RetrieveAPIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    serializer_class = OMRNPSUploadStatusSerializer    
    queryset = OMRNPSUpload.objects.all()
    permission_classes = (IsOMRNPSUploadOwner, )


class OMRNPSIngestTaskStatusView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def get(self, request, pk):
        try:
            result = AsyncResult(f'PROCESS_NPS_ANSWERS_{pk}')

            task_status = {
                'status': result.status,
                'details': {'done': 0, 'total': 1}
            }

            if result.status == states.STARTED and result.info.get('done', None):
                task_status['details'] = result.info

            if task_status.get('status', '') == states.SUCCESS:
                omr_upload = OMRNPSUpload.objects.get(pk=pk)
                task_status['total_pages'] = omr_upload.total_pages

            return Response(task_status)
        except Exception as e:
            return Response(f'Erro na obtenção dos dados {e}', status=500)
        
class OMRNPSUploadErrorsView(RetrieveAPIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    queryset = OMRNPSUpload.objects.all()
    permission_classes = (IsAuthenticated, IsOMRNPSUploadOwner, )
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if user.can_see_all():
            queryset = queryset.filter(
                user__coordination_member__coordination__unity__client=user.client
            ).distinct().select_related('user').order_by('-created_at')
        else:
            queryset = queryset.filter(
                user__coordination_member__coordination__in=user.get_coordinations_cache()
            ).distinct().select_related('user').order_by('-created_at')

        return queryset
            
    def get_serializer_class(self):
        from rest_framework import serializers
        class OutpuSerializer(serializers.ModelSerializer):
            total_errors = serializers.IntegerField(source='get_total_errors')
            
            class Meta:
                fields = ['id', 'total_errors']
                model = OMRNPSUpload
                
        return OutpuSerializer