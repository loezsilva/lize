from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Subquery, OuterRef, Value, F
from django.db.models.functions import Coalesce, Round

from fiscallizeon.answers.models import FileAnswer
from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.omr.tasks.fix_answers.reprocess_file_answers import reprocess_file_answers

class Command(BaseCommand):
    help = 'Reprocessa FileAnswers com notas erradas'

    def handle(self, *args, **kwargs):
        exams = FileAnswer.objects.filter(
            student_application__application__exam__name__icontains="p1",
            student_application__student__client__name__icontains="decisã"
        ).annotate(
            question_weight=Round(
                Coalesce(
                    Subquery(ExamQuestion.objects.availables(exclude_annuleds=True).filter(
                        question=OuterRef('question'),
                        exam=OuterRef('student_application__application__exam')
                    ).distinct().values('weight')[:1]),
                    Value(Decimal(0))
                ), 4
            ),
        ).filter(
            who_corrected__isnull=True,
            arquivo__isnull=False,
            teacher_grade__gt=F('question_weight'),
        ).distinct().values('student_application__application__exam')

        file_answers1 = FileAnswer.objects.filter(
            student_application__student__client="a2b1158b-367a-40a4-8413-9897057c8aa2",
            student_application__application__exam__name__icontains="p1",
            teacher_grade__gt=0,
            arquivo__isnull=False, 
            who_corrected__isnull=True
        ).annotate(
            question_weight=Subquery(
                ExamQuestion.objects.filter(
                    question=OuterRef('question'),
                    exam=OuterRef('student_application__application__exam'),
                ).distinct().values('weight')[:1]
            )
        ).annotate(
            mod=Round(F('teacher_grade') / F('question_weight'), 2),
        ).exclude(
            mod__in=[0.00, 0.25, 0.50, 0.75, 1.00]
        ).values_list('pk', flat=True)

        file_answers2 = FileAnswer.objects.filter(
            student_application__application__exam__in=exams,
            who_corrected__isnull=True,
            arquivo__isnull=False,
            teacher_grade__gt=0,
        ).values_list('pk', flat=True)

        answers_pks = set(list(file_answers1) + (list(file_answers2)))

        for file_answer in FileAnswer.objects.filter(pk__in=answers_pks):
            print(f'Answer em fila: {file_answer.pk}')
            reprocess_file_answers.apply_async(
                args=[file_answer.pk],
            )