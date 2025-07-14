
from fiscallizeon.exams.models import Exam
from fiscallizeon.clients.models import TeachingStage

stage_p1 = TeachingStage.objects.get(pk="c3e18aa9-22a3-4c52-8a93-f14d00a1612c")
stage_p2 = TeachingStage.objects.get(pk="93dfe0c9-077e-42e7-a457-89ca0ceff19a")

#cliente decisão
exams_p1 = Exam.objects.filter(
    coordinations__unity__client="a2b1158b-367a-40a4-8413-9897057c8aa2",
    name__icontains="P1",
    created_at__year=2023
).distinct()

exams_p1.update(teaching_stage=stage_p1)    

exams_p2 = Exam.objects.filter(
    coordinations__unity__client="a2b1158b-367a-40a4-8413-9897057c8aa2",
    name__icontains="P2",
    created_at__year=2023
).distinct()

exams_p2.update(teaching_stage=stage_p2)