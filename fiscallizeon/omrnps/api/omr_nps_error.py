from rest_framework import generics

from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.omrnps.models import OMRNPSError
from fiscallizeon.omrnps.serializers.omr_nps_error import OMRNPSErrorIdsSerializer


class OMRNPSErrorDeleteView(generics.DestroyAPIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    queryset = OMRNPSError.objects.all()
    serializer_class = OMRNPSErrorIdsSerializer