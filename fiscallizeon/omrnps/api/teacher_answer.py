from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response

from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.omrnps.models import TeacherAnswer
from fiscallizeon.omrnps.serializers.teacher_answer import TeacherAnswerSerializer


class TeacherAnswerCreateUpdateView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def post(self, request, *args, **kwargs):
        serializer = TeacherAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        teacher_answer, _ = TeacherAnswer.objects.using('default').update_or_create(
            teacher=serializer.validated_data.get('teacher'),
            nps_application_axis=serializer.validated_data.get('nps_application_axis'),
            omr_nps_page=serializer.validated_data.get('omr_nps_page'),
            defaults={
                'grade': serializer.validated_data.get('grade'),
                'created_by': request.user,
            }
        )

        return Response({**serializer.data, 'id': str(teacher_answer.pk)}, status=200)

class TeacherAnswerDeleteView(generics.DestroyAPIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    queryset = TeacherAnswer.objects.all()
    serializer_class = TeacherAnswerSerializer