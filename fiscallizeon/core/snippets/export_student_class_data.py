import csv
from fiscallizeon.students.models import Student

students = Student.objects.filter(
    client__name__icontains="ph",
    classes__school_year=2022
)

result = []

for student in students:
    for c in student.classes.filter(school_year=2022).distinct():
        line=[]
        line.append(student.name)
        line.append(student.enrollment_number)
        line.append(c.name)
        line.append(c.coordination.unity.name)
        result.append(line)

header = ["Nome", "Matrícula", "Turma", "Unidade"]

with open('students_ph_27_set.csv', 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(header)
    writer.writerows(result)