import time
from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand

from fiscallizeon.exams.models import Exam
from django.db.models import Case, When, Value, Q, Exists, OuterRef
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.answers.models import OptionAnswer, FileAnswer, TextualAnswer, SumAnswer
class Command(BaseCommand):
    help = 'Command para gerar performance de dados agrupados das provas.'
    def handle(self, *args, **kwargs):
        start_time = time.time()
        now = timezone.now()
        yesterday = (now - timedelta(days=1)).date()
        message_message = f"******* O Processo de geração de performances foi fizalizado com sucesso e demorou: "
        options = list(set(list(OptionAnswer.objects.filter(
            updated_at__date__gte=yesterday
        ).values_list("student_application__application__exam_id", flat=True))))
        print("fim_options", f"{time.time() - start_time} segundos *******")
        files =  list(set(list(FileAnswer.objects.filter(
            updated_at__date__gte=yesterday
        ).values_list("student_application__application__exam_id", flat=True))))
        print("fim_files", f"{time.time() - start_time} segundos *******")
        textuals = list(set(list(TextualAnswer.objects.filter(
            updated_at__date__gte=yesterday
        ).values_list("student_application__application__exam_id", flat=True))))
        print('fim textuals', f"{time.time() - start_time} segundos *******")
        sums = list(set(list(SumAnswer.objects.filter(
            updated_at__date__gte=yesterday
        ).values_list("student_application__application__exam_id", flat=True))))
        print('fim sums', f"{time.time() - start_time} segundos *******")
        exams_pks = list(set(options+files+textuals+sums))
        final_exams_pks = list(set(list(Exam.objects.filter(
            Q(
                Q(pk__in=exams_pks) if exams_pks else Q() |
                Q(updated_at__date__gte=yesterday) | 
                Q(examquestion__updated_at__date__gte=yesterday)
            )
        ).values_list('id'))))
        print("Exams - ", len(final_exams_pks), f"{time.time() - start_time} segundos *******")
        for exam_pk in final_exams_pks:
            e = Exam.objects.get(pk=exam_pk[0])
            e.run_recalculate_task()
        return message_message + f"{time.time() - start_time} segundos *******"