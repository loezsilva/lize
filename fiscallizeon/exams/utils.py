import datetime
from typing import List
from fiscallizeon.clients.models import SchoolCoordination
from fiscallizeon.exams.models import Exam

def is_exam_name_unique(coordinations, name, update=False, pk=None):
    if coordinations and name:
        selected_coordinations = SchoolCoordination.objects.filter(pk__in=coordinations)

        client = selected_coordinations.first().unity.client

        year = Exam.objects.get(pk=pk).created_at.year if pk else datetime.datetime.now().year

        exams_with_same_name = Exam.objects.filter(
            name__iexact=name, 
            coordinations__unity__client=client, 
            created_at__year=year
        ).exclude(pk=pk)
        
        return not exams_with_same_name.exists()
    return True