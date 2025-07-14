from rest_framework.generics import ListAPIView

from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.omrnps.models import TeacherOrder, OMRNPSPage
from fiscallizeon.omrnps.serializers.teacher_order import TeacherOrderSerializer


class TeacherOrderListView(ListAPIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    serializer_class = TeacherOrderSerializer
    queryset = TeacherOrder.objects.all()

    def get_queryset(self):
        nps_page = OMRNPSPage.objects.get(pk=self.kwargs.get('pk'))
        return TeacherOrder.objects.filter(
            class_application=nps_page.class_application
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['nps_page'] = self.kwargs.get('pk')
        return context