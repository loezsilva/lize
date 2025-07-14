import csv
from fiscallizeon.students.models import Student
from fiscallizeon.classes.models import Grade

students = Student.objects.filter(
    user__isnull=False,
    classes__school_year=2023,
    client__name__icontains="decisão"
).distinct()

header = ["nome","email","usuario","senha","matricula","turmas","email_responsavel","coordenacao_id","serie"]

with open('alunos_decisao_.csv', 'w', encoding='UTF8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(header)
    for student in students:
        writer.writerow([
            student.name,
            student.email,
            student.user.username,
            "Mudar123@",
            student.enrollment_number,
            student.get_last_class().name,
            student.responsible_email,
            str(student.get_last_class().coordination.pk),
            f'M{student.get_last_class().grade.name}' if student.get_last_class().grade.level == Grade.HIGHT_SCHOOL else f'F{student.get_last_class().grade.name}'
        ])