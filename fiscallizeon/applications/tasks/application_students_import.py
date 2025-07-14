import pandas as pd
from fiscallizeon.accounts.models import User
from fiscallizeon.applications.models import Application
from fiscallizeon.celery import app
from django.db import IntegrityError, transaction

from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.exports.models import Import
from fiscallizeon.students.models import Student

from celery import states

@app.task(bind=True, )
def application_students_import(self, user_id, csv_file_url):
    csv_content = pd.read_csv(csv_file_url, dtype=str)
    user = User.objects.get(pk=user_id)

    importation = Import.objects.create(
            type=Import.APPLICATION_STUDENTS,
            created_by=user,
            file_url=csv_file_url,
        )
    
    all_errors = []
    
    try:
        with transaction.atomic():
            for index, line in csv_content.iterrows():
                line_type = line['tipo (aluno ou turma)'].strip()
                application = Application.objects.filter(exam__name=line['nome da prova']).first()
                if not application:
                    all_errors.append(f"Prova {line['nome da prova']} não encontrada.")

                if line_type == 'aluno':
                    student_identifier = line['identificador (nome da turma ou matrícula do aluno)'].strip()

                    try:
                        student = Student.objects.filter(enrollment_number=student_identifier, client__in=user.get_clients_cache()).distinct().first()
                        if not student:
                            all_errors.append(f"Aluno {student_identifier} não encontrado.")
                            continue
                        # print(f"adicionando aluno {student}")
                        application.students.add(student)
                        application.save()

                    except Student.DoesNotExist:
                        all_errors.append(f"Aluno {student_identifier} não encontrado.")
                        continue

                elif line_type == 'turma':
                    class_identifier = line['identificador (nome da turma ou matrícula do aluno)'].strip()
                    
                    try:
                        unity = line['unidade'].strip()
                        class_ = SchoolClass.objects.filter(name=class_identifier, coordination__unity__name=unity, coordination__unity__client__in=user.get_clients_cache()).distinct().first()
                        if not class_:
                            all_errors.append(f"Turma {class_identifier} não encontrada.")
                            continue
                        students_in_class = class_.students.filter(user__is_active=True)
                        # print("adicionando turma", class_)

                        application.students.add(*students_in_class)
                        application.school_classes.add(class_)
                        application.save()
                        
                    except SchoolClass.DoesNotExist:
                        all_errors.append(f"Turma {class_identifier} não encontrada.")
                        continue

                else:
                    all_errors.append(f"Tipo de linha {line_type} não reconhecido.")
                    continue

    except Exception as e:
        print("Erro ao importar alunos", e)
        all_errors.append(f"Erro ao importar alunos: {e}")
        
    if all_errors:
        importation.errors = all_errors
        importation.save()
        self.update_state(state=states.FAILURE)
        return "A importação foi finalizada com erro(s)."

    return "Importação de alunos em aplicações finalizada com sucesso."