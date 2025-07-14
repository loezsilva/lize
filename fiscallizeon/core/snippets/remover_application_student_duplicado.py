
from django.db.models import Q, OuterRef, Count, Subquery

from fiscallizeon.clients.models import Client
from fiscallizeon.applications.models import Application, ApplicationStudent


clients = Client.objects.filter(name__icontains="nova educac")
for client in clients:
    repeateds_applications = Application.objects.filter(
        created_at__year=2024,
        created_at__month__in=[6,7,8],
        exam__coordinations__unity__client=client, 
        category__in=[Application.MONITORIN_EXAM,Application.HOMEWORK]
    ).distinct().annotate(
        count=Count(
            Subquery(
                Application.objects.filter(
                    exam=OuterRef('exam'),
                    created_at__date=OuterRef('created_at__date'),
                    created_at__hour=OuterRef('created_at__hour'),
                    created_at__minute=OuterRef('created_at__minute'),
                    # created_at__second=OuterRef('created_at__second'),
                ).distinct().exclude(
                    pk=OuterRef('pk')
                ).order_by('created_at').values('pk')[:1]
            )
        )
    ).filter(
        count__gt=0
    ).order_by('exam__name','created_at')
    for app in repeateds_applications.order_by('exam__name','created_at'):
        print(app.created_at, app.exam.name, app.count)
    if repeateds_applications.count() > 0:
        print(client.name, repeateds_applications.count())


already_removed = []
studend_alredy_removed = []
manter_apps = []
for original_app in repeateds_applications.all().distinct():
    if str(original_app.pk) in already_removed:
        continue
    app_repeteads = repeateds_applications.filter(
        exam=original_app.exam
    )
    already_removed.extend(
        [str(app.pk) for app in app_repeteads]
    )
    all_apps_students = ApplicationStudent.objects.filter(
        application__in=app_repeteads,
    ).distinct()
    for stu in all_apps_students:
        if str(stu.pk) in studend_alredy_removed:
            continue
        deleted_students = ApplicationStudent.objects.filter(
            Q(student=stu.student),
            Q(application__exam=stu.application.exam),
            Q(option_answers__isnull=True),
            Q(file_answers__isnull=True),
            Q(textual_answers__isnull=True)
        ).exclude(  
            Q(
                Q(pk=stu.pk) |
                Q(pk__in=manter_apps)
            )
        )
        print(stu.application.exam.name, stu.student.name, deleted_students.count(), stu.pk)
        if deleted_students.count() > 0:
            deleted_students.delete()
            manter_apps.append(str(stu.pk))
            studend_alredy_removed.extend(
                [str(deleted_student.pk) for deleted_student in deleted_students]
            )




# DELETAR UMA DAS APLICAÇÕES
- CONSIDERAR OS APPSTUDENTS QUE JÁ POSSUEM REPSOSTA 
    - CONSIDERAR TODAS AS RESPOSTAS
- SE O ALUNO NÃO POSSUIR RESPOSTA EM NENHUMA APAGAR O APPSTUDENT DO APP QUE SERÁ APAGADO



for original_app in repeateds_applications.all():
    if str(original_app.pk) in already_removed:
        continue
    print("############", original_app.exam.name)
    app_repeteads = repeateds_applications.filter(
        exam=original_app.exam
    ).exclude(
        pk=original_app.pk
    )
    already_removed.extend(
        [str(app.pk) for app in app_repeteads]
    )
    original_app_students = ApplicationStudent.objects.filter(application=original_app)
    repeteads_app_stu = ApplicationStudent.objects.filter(application__in=app_repeteads)
    

    #todos que tem resposta na original
    students_that_responsers_original = original_app_students.filter(
        Q(
            Q(option_answers__isnull=False) |
            Q(file_answers__isnull=False) |
            Q(textual_answers__isnull=False)
        )
    ).distinct()
    for s in students_that_responsers_original:
        repeated_student_with_response = repeteads_app_stu.filter(
            Q(student=s.student),
            Q(
                Q(option_answers__isnull=True),
                Q(file_answers__isnull=True),
                Q(textual_answers__isnull=True)
            )
        ).distinct()
        if repeated_student_with_response.count() > 0:
            continue
        repeated_student_with_response.delete()

    # #todos os que não tem reposta
    # students_NOT_responsers_original = original_app_students.filter(
    #     Q(
    #         Q(option_answers__isnull=True), 
    #         Q(file_answers__isnull=True),
    #         Q(textual_answers__isnull=True)
    #     )
    # ).distinct()
    # for s in students_NOT_responsers_original:
    #     repeated_student_NOT_response = repeteads_app_stu.filter(
    #         Q(student=s.student),
    #         Q(
    #             Q(option_answers__isnull=True),
    #             Q(file_answers__isnull=True),
    #             Q(textual_answers__isnull=True)
    #         )
    #     ).distinct()
    #     repeated_student_NOT_response.delete()
    #     repeated_student_WITH_response = repeteads_app_stu.filter(
    #         Q(student=s.student),
    #         Q(e
    #             Q(option_answers__isnull=False) |
    #             Q(file_answers__isnull=False) |
    #             Q(textual_answers__isnull=False)
    #         )
    #     ).distinct()




# para importar uma lista de alunos em uma csv para um pood
import csv
from fiscallizeon.students.models import Student

students = Student.objects.filter(
    client__name__icontains="SESI - SP",
    user__is_active=True
)

with open('students3.csv', mode='w', newline='', encoding='utf-8') as file:
    escritor_csv = csv.writer(file)
    # Escrevendo o cabeçalho (opcional)
    escritor_csv.writerow(['Nome', 'Turma', 'Nota', 'Município', 'Unidade'])
    # Iterando sobre a lista de estudantes e escrevendo cada linha no CSV
    for s in students:
        last_class = s.get_last_class()
        escritor_csv.writerow([
            s.name, 
            last_class.name if last_class else '', 
            last_class.grade.name_grade if last_class else '', 
            last_class.coordination.unity.name if last_class else '',
            last_class.coordination.name if last_class else ''
        ])
