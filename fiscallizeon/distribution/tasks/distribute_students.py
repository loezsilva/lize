import os

from django.utils import timezone

from fiscallizeon.celery import app
from fiscallizeon.applications.models import Application
from fiscallizeon.distribution.models import RoomDistribution, Room
from fiscallizeon.distribution import functions


@app.task(bind=True)
def distribute_students(self, room_distribution_pk, selected_rooms_pks, applications_pks):
    room_distribution = RoomDistribution.objects.using('default').get(pk=room_distribution_pk)
    selected_rooms = Room.objects.filter(pk__in=selected_rooms_pks)

    try:
        self.update_state(state='PROGRESS')
        if room_distribution.category == RoomDistribution.NAME_GRADE:
            functions.distribute_students_grade(room_distribution, selected_rooms)
        elif room_distribution.category == RoomDistribution.NAME_SCHOOLCLASS:
            functions.distribute_students_by_class(room_distribution, selected_rooms)
        elif room_distribution.category == RoomDistribution.NAME_SCHOOL_COORDINATION:
            functions.distribute_students_coordination(room_distribution, selected_rooms)
    except Exception as e:
        self.update_state(state='ERROR')
        room_distribution.status = RoomDistribution.OTHER
        room_distribution.save()
    
    room_distribution.status = RoomDistribution.WAITING_EXPORT
    room_distribution.save()

    applications = Application.objects.filter(pk__in=applications_pks)
    applications.update(room_distribution=room_distribution)
    self.update_state(state='SUCCESS')
