from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response

from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.omrnps.models import UnityAnswer
from fiscallizeon.omrnps.serializers.unity_answer import UnityAnswerSerializer


class UnityAnswerCreateUpdateView(APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def post(self, request, *args, **kwargs):
        serializer = UnityAnswerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        unity_answer, _ = UnityAnswer.objects.using('default').update_or_create(
            omr_nps_page=serializer.validated_data.get('omr_nps_page'),
            class_application=serializer.validated_data.get('omr_nps_page').class_application,
            defaults={
                'grade': serializer.validated_data.get('grade'),
                'created_by': request.user,
            }
        )

        return Response({**serializer.data, "id": unity_answer.pk}, status=200)
    

class UnityAnswerDeleteView(generics.DestroyAPIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    queryset = UnityAnswer.objects.all()
    serializer_class = UnityAnswerSerializer