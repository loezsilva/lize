from django.db.models import Count

from fiscallizeon.applications.models import ApplicationStudent, Application
from fiscallizeon.exams.models import Exam

exams = Exam.objects.using('default').filter(
    coordinations__unity__client='60c76b23-e58e-44de-997f-821f3b26993d',
    application__applicationstudent__is_omr=True,
    created_at__year=2023,
).distinct()

print("Total provas", exams.count())

for exam in exams:
    print("Prova", exam.name)
    students = list(ApplicationStudent.objects.using('default').filter(
        application__exam=exam,
        application__date__lt='2023-06-17',
    ).values('student').annotate(
        count=Count('pk')
    ).values('student').order_by().filter(count__gt=1))
    print("Alunos duplicados:", len(students))
    for student in students:
        print("Aluno:", student['student'])
        application_students = list(ApplicationStudent.objects.using('default').filter(
            application__exam=exam,
            student=student['student'],
            application__category=Application.PRESENTIAL,
        ).get_annotation_count_answers(
            only_total_grade=True
        ).order_by('-total_grade'))
        for a in application_students[1:]:
            ApplicationStudent.objects.using('default').get(pk=a.pk).delete()


            a.option_answers.all().delete()
            a.textual_answers.all().delete()
            a.file_answers.all().delete()
            a.attachments.all().delete()