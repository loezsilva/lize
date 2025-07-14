from django.db.models import Q
from fiscallizeon.exams.models import Exam
from fiscallizeon.answers.models import OptionAnswer
from fiscallizeon.applications.models import ApplicationStudent

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Ajusta respostas duplicadas de alunos em optionaswer'

    def add_arguments(self, parser):
        # parser.add_argument('quantity', nargs='+', type=int)
        pass

    def handle(self, *args, **kwargs):
    exams = Exam.objects.using('default').filter(
        Q(created_at__year=2022),
        Q(name__icontains="ph"),
        Q(
            Q(application__applicationstudent__start_time__isnull=False) |
            Q(application__applicationstudent__is_omr=True)
        )
    ).distinct().order_by('-created_at')[92:]
    exam_count = exams.count()
    for index, exam in enumerate(exams):
        print(f'>>> Prova {index} de {exam_count} - {exam.name}')
        students = ApplicationStudent.objects.using('default').filter(
            Q(application__exam=exam),
            Q(option_answers__isnull=False),
            Q(
                Q(start_time__isnull=False) |
                Q(is_omr=True)
            )
        ).distinct()
        students_count = students.count()
        for index, student in enumerate(students):
            if index % 50 == 0: 
                print(f'--- Aluno {index} de {students_count} - {student.student.name}')
            option_answers = OptionAnswer.objects.using('default').filter(
                status=OptionAnswer.ACTIVE,
                student_application=student
            ).distinct()
            for option_aswer in option_answers:
                try:
                    actual_answer = OptionAnswer.objects.using('default').get(pk=option_aswer.pk, status=OptionAnswer.ACTIVE)
                except:
                    continue
                duplicate_answers = OptionAnswer.objects.using('default').filter(
                    status=OptionAnswer.ACTIVE,
                    question_option__question=option_aswer.question_option.question,
                    student_application=option_aswer.student_application,
                    student_application__application__exam=option_aswer.student_application.application.exam
                ).distinct().exclude(
                    pk=option_aswer.pk
                )
                if duplicate_answers:
                    duplicate_answers.using('default').update(status=OptionAnswer.INACTIVE)
                    print("Resposta duplicada", option_aswer.student_application.student.name, duplicate_answers.count(), f'Questão {exam.number_print_question(option_aswer.question_option.question)}')