from datetime import time, timedelta
from django.db.models import Q
from django.db.models.aggregates import Count
from django.db.models.expressions import F
from rest_framework import serializers
from rest_framework.fields import SerializerMethodField
from fiscallizeon.core.print_colors import print_error, print_success
from fiscallizeon.students.models import Student
from fiscallizeon.clients.models import SchoolCoordination
from fiscallizeon.distribution.models import Room, RoomDistribution, RoomDistributionStudent



# ROOMS
class CoordinationRoomSimpleSerializer(serializers.ModelSerializer):
    unity_name = serializers.CharField(source='unity.name', default='')
    class Meta:
        model = SchoolCoordination
        fields = ['id', 'name', 'unity_name']

class StudentRoomSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['id', 'name']

class RoomSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'name']
        
class RoomAndCoordinationSimpleSerializer(serializers.ModelSerializer):
    coordination = CoordinationRoomSimpleSerializer()
    

    class Meta:
        model = Room
        fields = '__all__'

class AvailableRoomsSerializer(serializers.ModelSerializer):
    coordination = CoordinationRoomSimpleSerializer()
    number_vacancies_available = SerializerMethodField()

    class Meta:
        model = Room
        fields = ['id', 'name', 'coordination', 'capacity', 'number_vacancies_available']

    def get_number_vacancies_available(self, obj):
        queryset = obj.room_distribution.all().filter(
            Q(distribution__application__date=self.context['date']),
            Q(
                Q(distribution__application__start__range=[self.context['start'], self.context['end']]) |
                Q(distribution__application__end__range=[self.context['start'], self.context['end']])
            )
        )
        return 0 if queryset.exists() else obj.capacity


# ROOM DISTRIBUTION
class RoomDistributionSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomDistribution
        fields = '__all__'


class RoomDistributionSerilazer(serializers.ModelSerializer):

    rooms = SerializerMethodField()
    applications = SerializerMethodField()
    date = SerializerMethodField()

    class Meta:
        model = RoomDistribution
        fields = ['category', 'rooms', 'applications', 'date', 'is_printed']

    def get_applications(self, obj):
        applications = [application.id for application in obj.application_set.all().order_by('exam__name')]
        return applications

    def get_rooms(self, obj):
        rooms = [room.get('id') for room in obj.room_distribution.all().values('room').annotate(students_count=Count('student'), id=F('room__id'))]
        return rooms

    def get_date(self, obj):
        return obj.application_set.all().first().date








# ROOM DISTRIBUTION STUDENT
class RoomDistributionStuentSimpleSerializer(serializers.ModelSerializer):

    room = RoomSimpleSerializer()
    student = StudentRoomSimpleSerializer()
    
    class Meta:
        model = RoomDistributionStudent
        fields = ['id', 'student', 'room']


class RoomDistributionStuentSwapSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomDistributionStudent
        fields = ['student',]
class RoomDistributionStuentSwapRoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomDistributionStudent
        fields = ['room',]