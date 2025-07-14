from fiscallizeon.students.models import Student
students = Student.objects.filter(
    client__name__icontains="motivo",
    classes__school_year=2022
).distinct()
with open('tmp/provas_motivo.csv', 'w', encoding='UTF8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["Aluno", "Matrícula", "Unidade", "Turma", "Último acesso", "Quantidade de atividade iniciadas"])
    for student in students:
        application_students = student.applicationstudent_set.filter(
            start_time__isnull=False,
            created_at__year=2022
        ).distinct()
        writer.writerow([
            student.name.upper() or "Sem nome",
            student.enrollment_number or "Sem matrícula",
            student.get_last_class().coordination.unity.name if student.get_last_class() else "Sem unidade",
            student.get_last_class().name or "Sem turma",
            student.user.last_login or "Não entrou",
            application_students.count(),
        ])


    