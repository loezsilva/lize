from fiscallizeon.students.models import Student

students = Student.objects.filter(client='86ba20fe-3822-4f72-ab9a-01720bf93662')

for student in students:
    try:
        student.enrollment_number = student.email.split('-')[1]
        student.save()
        print(student.name)
    except:
        print("Deu erro", student)