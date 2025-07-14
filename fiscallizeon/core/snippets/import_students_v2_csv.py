import csv
import os
import requests
import shutil
import random
from django.db.models import Q
from fiscallizeon.students.models import Student
from fiscallizeon.clients.models import Unity, SchoolCoordination, CoordinationMember, Client
from fiscallizeon.accounts.models import User
from fiscallizeon.classes.models import SchoolClass, Grade
from fiscallizeon.students.models import Student
from django.utils import timezone
from fiscallizeon.applications.models import ApplicationStudent
class ImportStudent():
    path_file="https://fiscallizeremote.nyc3.cdn.digitaloceanspaces.com/temp/%5BMETA%5D%20Importacao_alunos_v2%20-%20META%20JP%20-%20TODOS%20ALUNOS.csv"
    def get_grade(self, grade_name):
        level = grade_name[0].upper()
        name = grade_name[1]
        if grade_name.lower() in ['curso', 'concurso']:
             return Grade.objects.filter(
                level=Grade.HIGHT_SCHOOL,
                name=grade_name
            ).first()
        if level == 'M':
            return Grade.objects.filter(
                level=Grade.HIGHT_SCHOOL,
                name=name
            ).first()
        if level == 'F':
            level = Grade.ELEMENTARY_SCHOOL if name in ['1', '2', '3', '4', '5'] else Grade.ELEMENTARY_SCHOOL_2
            return Grade.objects.filter(
                level=level,
                name=name
            ).first()
    def run(self):
        with requests.get(self.path_file, stream=True) as r:
            tmp_file = os.path.join("/tmp/curiar.csv")
            print("baixou o arquivo")
            with open(tmp_file, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
            with open(tmp_file, 'r') as file:
                csvreader = csv.DictReader(file)
                for index, row in enumerate(csvreader):
                    print(index)
                    student_name = row["nome"].upper().replace("  ", " ")
                    student_email = row['email'].upper().replace("  ", " ")
                    student_user = row['usuario'].upper().replace("  ", " ")
                    student_pass = row['senha'].upper().replace("  ", " ")
                    student_enrollment_number = row['matricula'].upper().replace("  ", " ")
                    students_classes = row['turmas'].split(",")
                    student_email_parent_1 = row['email_responsavel'].upper().replace("  ", " ")
                    student_email_parent_2 = row['email_responsavel_2'].upper().replace("  ", " ")
                    student_coordinations = row['coordenacao_id'].upper().replace("  ", " ")
                    student_grade = row['serie'].upper().replace("  ", " ")
                    coordination = SchoolCoordination.objects.using('default').filter(pk=student_coordinations).first()
                    exist_students = Student.objects.filter(
                        Q(client__name__icontains="colégio meta"),
                        Q(
                            Q(name=student_name) |
                            Q(enrollment_number=student_enrollment_number) |
                            Q(email__iexact=student_email)
                        )
                    ).distinct()
                    if exist_students.count() > 1:
                        current_student = exist_students.first()
                        for old_student in exist_students[2:]:
                            ApplicationStudent.objects.filter(
                                student=old_student
                            ).update(student=current_student)
                            old_student.name = old_student.name+" ERRADO22"
                            old_student.email = old_student.email+" ERRADO22"
                            old_student.enrollment_number = old_student.enrollment_number+" ERRADO22"
                            old_student.save(skip_hooks=True)
                    else:
                        current_student = exist_students.first()
                    current_student.name = student_name
                    current_student.email = student_email.lower()
                    current_student.enrollment_number = student_enrollment_number
                    current_student.responsible_email = student_email_parent_1.lower()
                    current_student.responsible_email_two = student_email_parent_2.lower()
                    current_student.save(skip_hooks=True)
                    exists_users = User.objects.filter(
                        Q(
                            Q(username__iexact=student_user) |
                            Q(email__iexact=student_email)
                        )
                    )
                    for user in exists_users:
                        user.username = user.username+str(int(random.random()*1000))
                        user.email = user.email+str(int(random.random()*1000))
                        user.is_active = False
                        user.save()
                    current_student.user.username = student_user.lower()
                    current_student.user.email = student_email.lower()
                    current_student.user.is_active = True
                    current_student.user.set_password(student_pass)
                    current_student.user.save()
                    old_classes = SchoolClass.objects.filter(
                        students__in=[current_student],
                        school_year=timezone.now().year
                    )
                    for old_class in old_classes:
                        old_class.students.remove(current_student)
                        old_class.save()
                    for csv_class in students_classes:
                        client_class = SchoolClass.objects.using('default').filter(
                            coordination=coordination,
                            name=csv_class.upper().strip(),
                            grade=self.get_grade(student_grade),
                            school_year=timezone.now().year,
                        ).using('default').first()
                        if not client_class:
                            print(coordination, csv_class.upper().strip(), student_grade, self.get_grade(student_grade))
                            client_class = SchoolClass.objects.create(
                                coordination=coordination,
                                name=csv_class.upper().strip(),
                                grade=self.get_grade(student_grade),
                                school_year=timezone.now().year,
                            )
                        if current_student in client_class.students.using('default').all():
                            continue
                        client_class.students.add(Student.objects.using('default').get(pk=current_student.pk))