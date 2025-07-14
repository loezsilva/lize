import pandas as pd
from celery import states

from django.db.models import Q
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction

from fiscallizeon.accounts.models import User
from fiscallizeon.students.models import Student
from fiscallizeon.classes.models import Grade, SchoolClass
from fiscallizeon.clients.models import SchoolCoordination

class Command(BaseCommand):
    help = 'Importa alunos de CSV'

    def add_arguments(self, parser):
        parser.add_argument('--file_url', nargs=1, type=str)

    def get_grade(self, grade_name):
        level = grade_name[0].upper()
        name = grade_name[1:]
        
        if grade_name.lower() in ['curso', 'concurso']:
                return Grade.objects.get(
                level=Grade.HIGHT_SCHOOL,
                name=grade_name
            )

        if level == 'M':
            return Grade.objects.get(
                level=Grade.HIGHT_SCHOOL,
                name=name
            )
        
        if level == 'F':
            level = Grade.ELEMENTARY_SCHOOL if name in ['1', '2', '3', '4', '5'] else Grade.ELEMENTARY_SCHOOL_2
            return Grade.objects.get(
                level=level,
                name=name
            )

    def handle(self, *args, **kwargs):
        user_id = "fc7af76e-a4ba-4459-84e6-cbc3e0e42a66"
        csv_file_url = kwargs['file_url'][0]
        replace_old_classes = True
        csv_content = pd.read_csv(csv_file_url, dtype=str)
        last_coordination = None
        coordination = None
        client = None
        # importation = None
        
        user = User.objects.get(pk=user_id)
        has_errors = False

        try:
            with transaction.atomic():

                for index, student in csv_content.iterrows():
                    print(index, student['email'])
                    if last_coordination != student['coordenacao_id'].strip():
                       
                        coordination = None
                        last_coordination = student['coordenacao_id'].strip()

                        coordination = SchoolCoordination.objects.using('default').select_related('unity__client').get(unity__client=user.client, pk=student['coordenacao_id'].strip())

                    student_db = Student.objects.select_related('user').using('default').filter(
                        Q(client=coordination.unity.client),
                        Q(
                            Q(enrollment_number=student['matricula'].strip()) |
                            Q(email=student['email'].strip())
                        )
                    ).first()

                    if not student_db:
                        student_db = Student(
                            client=coordination.unity.client,
                            name=student['nome'].strip(),
                            email=student['email'].strip(),
                            enrollment_number=student['matricula'].strip(),
                            responsible_email=student.get('email_responsavel', ''),
                            responsible_email_two=student.get('email_responsavel_2', ''),
                            responsible_email_three=student.get('email_responsavel_3', ''),
                            responsible_email_four=student.get('email_responsavel_4', ''),
                        )

                        student_db.create_user(
                            username=student['usuario'].strip(),
                            password=student['senha'].strip()
                        )
                        student_db.save(skip_hooks=True)
                    else:
                        student_db.name = student['nome'].strip()
                        student_db.email = student['email'].strip()
                        student_db.enrollment_number = student['matricula'].strip()
                        
                        if not student_db.responsible_email:
                            student_db.responsible_email=student.get('email_responsavel', '')
                        
                        if not student_db.responsible_email_two:
                            student_db.responsible_email_two=student.get('email_responsavel_2', '')
                        
                        if not student_db.responsible_email_three:
                            student_db.responsible_email_three=student.get('email_responsavel_3', '')
                        
                        if not student_db.responsible_email_four:
                            student_db.responsible_email_four=student.get('email_responsavel_4', '')
                        
                        student_db.user.name = student['nome'].strip()
                        student_db.user.email = student['email'].strip()
                        student_db.user.is_active = True
                        student_db.user.save() 
                        student_db.save(skip_hooks=True)

                    if replace_old_classes:
                        old_classes = SchoolClass.objects.filter(
                            students__in=[student_db],
                            school_year=2024
                        )

                        for old_class in old_classes:
                            old_class.students.remove(student_db)
                            old_class.save()
                            for application in old_class.applications.all():
                                if application.student_can_be_remove_or_add:
                                    application.students.remove(student_db.pk)

                    csv_classes = student['turmas'].split(',')

                    for csv_class in csv_classes:
                        grade = self.get_grade(student['serie'])
                        client_class = SchoolClass.objects.using('default').filter(
                            coordination=coordination,
                            name=csv_class.upper().strip(),
                            grade=grade,
                            school_year=2024,
                        ).using('default').first()

                        if not client_class:
                            client_class = SchoolClass.objects.create(
                                coordination=coordination,
                                name=csv_class.upper().strip(),
                                grade=grade,
                                school_year=2024,
                            )
                        for application in client_class.applications.all():
                            if student_db not in application.students.all() and not application.is_time_finished and application.student_can_be_remove_or_add:
                                application.students.add(student_db.pk)

                        if student_db in client_class.students.using('default').all():
                            continue

                        client_class.students.add(Student.objects.using('default').get(pk=student_db.pk))

        except Exception as e:
            
            linha = index + 1
            
            has_errors = True
            
            # all_errors = list(importation.errors or [])
            
            if type(e) == SchoolCoordination.DoesNotExist:
                
                last_coordination = None
                coordination = None
                print(f"Erro na linha {linha}: A coordenação do aluno {student['nome']} não foi encontrada")

            elif type(e) == IntegrityError:

                print(f"Erro na linha {linha}: O aluno {student['nome']} com o e-mail {student['email']} já existe, altere o email do aluno e tente importar novamente.")

            elif type(e) == Grade.DoesNotExist:

                print(f"Erro na linha {linha}: A série do aluno {student['nome']} não foi encontrada")
            
            elif type(e) == KeyError:
                
                column_error_message = f"Erro na planilha, uma das colunas obrigatórias não foi encontrada."
                print(column_error_message)
            
            else:
                
                print('Erro desconhecido: ', e)
                print(f"Erro na linha {linha}: Ocorreu um erro desconhecido, entre em contato com o suporte para maiores informações")

        
        if has_errors:
            print("A importação foi finalizada mas retornou um erro.")

        print("Importação de alunos finalizada com sucesso.")