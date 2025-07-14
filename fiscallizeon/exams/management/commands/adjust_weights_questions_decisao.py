from decimal import Decimal
from django.core.management.base import BaseCommand

from fiscallizeon.exams.models import Exam
from fiscallizeon.core.utils import round_half_up


class Command(BaseCommand):
    help = 'Ajusta nota de cadernos p1 do decisão'

    def handle(self, *args, **kwargs):
        exams = Exam.objects.filter(
            name__icontains="P5",
            coordinations__unity__client__name__icontains="decisão",
            created_at__year=2023
        ).distinct().order_by('name')

        for exam in exams:
            availables = exam.examquestion_set.availables().order_by('exam_teacher_subject__order', 'order')
            availables_without_annuled = availables.availables(exclude_annuleds=True).order_by('exam_teacher_subject__order', 'order')
            count = availables.count()
            count_without_annuled = availables_without_annuled.count()
            if count_without_annuled == 0:
                continue
            question_weight = 10/count_without_annuled
            if count == 11:
                question_weight = 10/(count_without_annuled-1)
            question_weight = Decimal(question_weight).quantize(Decimal('0.00001'))
            print("{:0>2} {:0>2} {} {:<50} {}".format(count, count_without_annuled, question_weight, exam.name, exam.pk))
            for exam_question in availables_without_annuled:
                if "deveriam estar nesta prova" in exam_question.question.enunciation.lower():
                    print(exam_question.question.enunciation)
                    exam_question.weight = 0
                    exam_question.save()
                    continue
                exam_question.weight = question_weight
                exam_question.save()