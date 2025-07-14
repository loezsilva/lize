from django.contrib.auth.models import Group
from django.db.models.aggregates import Count
from django.db.models.expressions import F, ExpressionWrapper
from django.db.models.fields import SmallIntegerField
from rest_framework.authentication import BasicAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.core.utils import CheckHasPermission
from rest_framework.filters import SearchFilter
from rest_framework import generics, status
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth.mixins import LoginRequiredMixin

from fiscallizeon.distribution.models import Room, RoomDistributionStudent
from fiscallizeon.distribution.serializers.distribution import AvailableRoomsSerializer, RoomAndCoordinationSimpleSerializer, RoomDistributionStuentSimpleSerializer, RoomDistributionStuentSwapRoomSerializer, RoomDistributionStuentSwapSerializer

from rest_framework.renderers import JSONRenderer


class RoomListAPIView(LoginRequiredMixin, CheckHasPermission, generics.ListAPIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    model = Room
    serializer_class = AvailableRoomsSerializer
    filter_backends = [SearchFilter, DjangoFilterBackend]
    queryset = Room.objects.all()
    search_fields = ('id', )

    def get_queryset(self):
        self.queryset = self.queryset.filter(
            coordination__unity__client__in=self.request.user.get_clients_cache(),
        ).distinct()

        if self.request.GET.get('coordinations'):
            self.queryset = self.queryset.filter(coordination__in=self.request.GET.getlist('coordinations'))

        if self.request.GET.get('unitys'):
            self.queryset = self.queryset.filter(coordination__unity__in=self.request.GET.getlist('unitys'))

        return self.queryset

    def get_serializer_context(self):
        context = super(RoomListAPIView, self).get_serializer_context()
        context["date"] = self.request.GET.get('date')
        context["start"] = self.request.GET.get('start')
        context["end"] = self.request.GET.get('end')
        return context


class GroupRoomOfRoomDistributionStudentListAPIView(LoginRequiredMixin, CheckHasPermission, APIView):
    renderer_classes = [JSONRenderer]
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def get(self, request, *args, **kwargs):
        
        roomdistributionstudent = RoomDistributionStudent.objects.filter(room__coordination__in=self.request.user.get_coordinations_cache())
        
        if self.request.GET.get('pk') and self.request.GET.get('student_room'):
            roomdistributionstudent = roomdistributionstudent.filter(distribution=self.request.GET.get('pk')).exclude(room=self.request.GET.get('student_room', ''))


        rooms_annotations = roomdistributionstudent.values('room').annotate(
            id = F('room__id'),
            name = F('room__name'),
            room_capacity = F('room__capacity'),
            students_count = Count('student'),
            number_vacancies_available = ExpressionWrapper(F('room_capacity') - F('students_count'), output_field=SmallIntegerField()),
        )

        return Response(status=status.HTTP_200_OK, data= {
                "rooms": rooms_annotations,
            }, content_type="application/json")


class RoomDistributionStudentListAPIView(LoginRequiredMixin, CheckHasPermission, generics.ListAPIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    model = RoomDistributionStudent
    serializer_class = RoomDistributionStuentSimpleSerializer
    queryset = RoomDistributionStudent.objects.all()
    filter_backends = [SearchFilter, DjangoFilterBackend]
    filterset_fields = ['distribution', 'room']


class RoomDistributionStudentSwapUpdateAPIView(LoginRequiredMixin, CheckHasPermission, generics.UpdateAPIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    model = RoomDistributionStudent
    serializer_class = RoomDistributionStuentSwapSerializer
    queryset = RoomDistributionStudent.objects.all()


    def update(self, request, *args, **kwargs):

        old_distribution_student = RoomDistributionStudent.objects.get(pk=kwargs.get('old_pk'))
        old_distribution_student.student = self.get_object().student
        old_distribution_student.save()

        return super(RoomDistributionStudentSwapUpdateAPIView, self).update(request, *args, **kwargs)


class RoomDistributionStudentSwapRoomUpdateAPIView(LoginRequiredMixin, CheckHasPermission, generics.UpdateAPIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )
    model = RoomDistributionStudent
    serializer_class = RoomDistributionStuentSwapRoomSerializer
    queryset = RoomDistributionStudent.objects.all()


rooms_list = RoomListAPIView.as_view()
group_rooms_of_roomdistributions_list = GroupRoomOfRoomDistributionStudentListAPIView.as_view()
roomdistributionstudent_list = RoomDistributionStudentListAPIView.as_view()

roomdistributionstudent_swap_update = RoomDistributionStudentSwapUpdateAPIView.as_view()
roomdistributionstudent_swap_room_update = RoomDistributionStudentSwapRoomUpdateAPIView.as_view()