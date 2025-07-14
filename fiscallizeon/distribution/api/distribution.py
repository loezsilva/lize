
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.generics import RetrieveAPIView, UpdateAPIView
from django.conf import settings

from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.distribution.models import RoomDistribution
from fiscallizeon.distribution.serializers.distribution import RoomDistributionSerilazer

from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from rest_framework.authentication import BasicAuthentication

class RoomDistributionRetrieveAPIView(LoginRequiredMixin, CheckHasPermission, RetrieveAPIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    model = RoomDistribution
    queryset = RoomDistribution.objects.all()
    serializer_class = RoomDistributionSerilazer
    
class RoomDistributionUpdatePIView(LoginRequiredMixin, CheckHasPermission, UpdateAPIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    model = RoomDistribution
    queryset = RoomDistribution.objects.all()
    serializer_class = RoomDistributionSerilazer

roomdistribution_detail = RoomDistributionRetrieveAPIView.as_view()
roomdistribution_update = RoomDistributionUpdatePIView.as_view()