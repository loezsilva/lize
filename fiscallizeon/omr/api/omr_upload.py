from rest_framework.generics import RetrieveAPIView, UpdateAPIView, DestroyAPIView
from rest_framework.views import APIView
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.omr.models import OMRError, OMRUpload, OMRStudents
from fiscallizeon.omr.serializers.omr_upload import OMRStudentsStatusSerializer, OMRStudentsUpdateSerializer, OMRUploadStatusSerializer
from fiscallizeon.omr.permissions import IsOMRUploadOwner
from rest_framework.response import Response
from django.utils import timezone
from rest_framework import status
from django.shortcuts import get_object_or_404

class OMRUploadStatusView(RetrieveAPIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    serializer_class = OMRUploadStatusSerializer    
    queryset = OMRUpload.objects.all()
    permission_classes = (IsOMRUploadOwner, )
    

class OMRStudentsHistoricalRerieveAPIView(RetrieveAPIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    serializer_class = OMRStudentsStatusSerializer    
    queryset = OMRStudents.objects.all()


class OmrStudentsUploadCheckUpdateAPIView(UpdateAPIView):
    serializer_class = OMRStudentsUpdateSerializer
    queryset = OMRStudents.objects.using('default').all()
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.checked = not instance.checked
        instance.checked_by = self.request.user
        instance.save()
        return Response(instance.checked)

class OmrUploadStudentPageErrorCount(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    def get(self, request, pk):
        omr_upload = OMRUpload.objects.get(pk=self.kwargs['pk'])
        if student_page_error_count := omr_upload.student_page_error_count:
            return Response({"id": omr_upload.id, "count": student_page_error_count })
        return Response({"id": omr_upload.id, "count": 0})

omr_upload_status = OMRUploadStatusView.as_view()

class OmrUploadStudentPageErrorCountAndStudents(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    def get(self, request, pk):
        omr_upload = OMRUpload.objects.get(pk=self.kwargs['pk'])
        
        objects = []
        for omr_student in omr_upload.omrstudents_set.all():
            answers_questions = omr_student.application_student.total_answered_questions()
            total_questions = omr_student.count_questions
            if answers_questions < total_questions:
                objects.append({
                    "upload_id": self.kwargs['pk'],
                    "id": str(omr_student.id),
                    "name": omr_student.application_student.student.name,
                    "total_answers_questions": answers_questions,
                    "application_student": {
                        "id": omr_student.application_student.id,
                    },
                    "total_questions": total_questions,
                    "checked": omr_student.checked,
                })
        
        return Response(
            objects
        )
        
class OMRUploadSimpleUpdateAPIView(UpdateAPIView):
    from rest_framework import serializers
    
    class OMRUploadVerySimpleSeiralizer(serializers.ModelSerializer):
        class Meta:
            fields = ['corrected', 'seen']
            model = OMRUpload
        
    serializer_class = OMRUploadVerySimpleSeiralizer
    authentication_classes = (CsrfExemptSessionAuthentication, )
    queryset = OMRUpload.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        if self.request.user.can_see_all():
            queryset = queryset.filter(
                user__coordination_member__coordination__unity__client__in=self.request.user.get_clients_cache()
            ).distinct().select_related('user').order_by('-created_at')
        else:
            queryset = queryset.filter(
                user__coordination_member__coordination__in=self.request.user.get_coordinations_cache()
            ).distinct().select_related('user').order_by('-created_at')
            
        return queryset
    
class OMRDeleteErrorApi(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    def post(self, request, *args, **kwargs):
        error = OMRError.objects.get(pk=request.data.get('pk'))
        error.is_solved = True
        error.is_associated_file = False
        error.save()
        
        return Response(f"deleted error {error.pk}")
    
class OMRAssociatedFileApi(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    def patch(self, request, *args, **kwargs):
        pk = kwargs['pk']
        omr = get_object_or_404(OMRError.objects.using('default'), pk=pk)
        omr.is_associated_file = not omr.is_associated_file
        omr.is_solved = omr.is_associated_file
        omr.save()
        
        return Response(f"alter omr {pk}")


class OMRSoftDeleteAPi(DestroyAPIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )

    queryset = OMRUpload.objects.exclude(deleted_at__isnull=False)
    
    def get_queryset(self):
        user = self.request.user
        queryset = super().get_queryset()
        queryset = queryset.filter(
            user__coordination_member__coordination__unity__client=user.client,
        )
            
        return queryset.distinct()

    def destroy(self, request, *args, **kwargs):
        omr_upload = get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])
        omr_upload.deleted_at = timezone.now()
        omr_upload.deleted_by = self.request.user
        omr_upload.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

omr_upload_status = OMRUploadStatusView.as_view()