from fiscallizeon.students.models import Student

student = Student.objects.get(pk='40aea02e-28a2-403a-9c22-11375978761f')

grade = student.applicationstudent_set.filter(
    application__exam='04879ab1-4300-45de-9fa9-845a21635c9d'
).order_by('created_at').get_annotation_count_answers(
    only_total_grade=True,
    exclude_annuleds=True,
)[0].total_grade

print(grade)