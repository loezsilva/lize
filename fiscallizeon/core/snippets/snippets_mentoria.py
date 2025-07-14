from fiscallizeon.applications.models import ApplicationStudent
from django.db.models.functions import TruncMinute
from django.db.models import Count

# Gera todas as datas únicas com truncamento por minuto
from django.db.models import Func, F, Value, CharField
from fiscallizeon.applications.models import ApplicationStudent


class ToChar(Func):
    function = "TO_CHAR"
    template = "%(function)s(%(expressions)s, 'DD-MM-YYYY HH24:MI')"
    output_field = CharField()


students = (
    ApplicationStudent.objects.filter(
        application="e8bb3395-e14f-4a20-8de9-669b850e4a6a", start_time__isnull=False
    )
    .annotate(start_time_str=ToChar(F("start_time")))
    .annotate(end_time_str=ToChar(F("end_time")))
    .order_by("start_time")
)

datas_unicas_start = (
    students.values_list("start_time_str", flat=True)
    .distinct()
    .order_by("start_time_str")
)

datas_unicas_end = (
    students.values_list("end_time_str", flat=True).distinct().order_by("end_time_str")
)

datas_unicas = list(set(datas_unicas_start).union(set(datas_unicas_end)))

for data in datas_unicas_end:
    # students_start_at = students.filter(start_time_str=data).distinct()
    finished = students.filter(end_time_str=data).distinct()
    print(f"{data},{finished.count()}")
