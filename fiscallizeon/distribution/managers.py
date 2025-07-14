from django.db import models
from django.db.models import Q, F, Count, Subquery, OuterRef
from django.utils import timezone
from django.apps import apps

from fiscallizeon.classes.models import SchoolClass

class RoomQuerySet(models.QuerySet):

    def filter_by_application_date(self, date, start, end):
        return self.filter(
            room_distribution__distribution__application__date=date,
            room_distribution__distribution__application__start=start,
            room_distribution__distribution__application__end=end
        ).distinct()

    def get_occupation(self, date, start, end):
        return self.annotate(
            occupation=Count('room_distribution', filter=Q(
                room_distribution__distribution__application__date=date,
                room_distribution__distribution__application__start=start,
                room_distribution__distribution__application__end=end,
            ))
        )

    def get_first_student_grade_and_class(self, date, start, end):
        """
        Return the grade of the first student in the room.
        """
        Student = apps.get_model('students', 'Student')

        student_subquery =  Student.objects.add_last_class().filter(
            pk=OuterRef('room_distribution__student__pk'),
            room_distribution__distribution__application__date=date,
            room_distribution__distribution__application__start=start,
            room_distribution__distribution__application__end=end,
        ).distinct()

        return self.annotate(
            first_student_grade=Subquery(
                student_subquery.values('last_class_grade')[:1]
            ),
            first_student_school_class=Subquery(
               student_subquery.values('last_class')[:1]
            )
        ).distinct()

    def get_first_room_distribution(self, date, start, end):
        """
        Return the first room_distribution of the room.
        """
        RoomDistribution = apps.get_model('distribution', 'RoomDistribution')

        return self.annotate(
            first_room_distribution=Subquery(
                RoomDistribution.objects.filter(
                    pk=OuterRef('room_distribution__distribution__pk'),
                    room_distribution__distribution__application__date=date,
                    room_distribution__distribution__application__start=start,
                    room_distribution__distribution__application__end=end,
                ).values('pk')[:1]
            )
        )

RoomManager = models.Manager.from_queryset(RoomQuerySet)