import math
from celery import states
from decimal import Decimal
import pandas as pd
from django.db import transaction, IntegrityError
from django.db.models import Q, Max
from datetime import datetime

from fiscallizeon.celery import app
from fiscallizeon.accounts.models import User
from fiscallizeon.exams.models import Exam, ExamTeacherSubject, TeacherSubject, ExamOrientation, ExamQuestion
from fiscallizeon.clients.models import SchoolCoordination, TeachingStage, EducationSystem
from fiscallizeon.exams.utils import is_exam_name_unique
from fiscallizeon.subjects.models import SubjectRelation, Subject, Grade
from fiscallizeon.exports.models import Import
from fiscallizeon.inspectors.models import Inspector
from django.utils import timezone

from fiscallizeon.answers.models import TextualAnswer
from fiscallizeon.applications.models import ApplicationStudent, Application
from fiscallizeon.corrections.models import CorrectionTextualAnswer, CorrectionCriterion
from fiscallizeon.questions.models import Question

import logging

logger = logging.getLogger(__name__)

def create_importation(user, file_url, type=Import.EXAMS):
    importation = Import.objects.create(
        type=type,
        created_by=user,
        file_url=file_url,
    )

    return importation

def clean_content(content):
    if isinstance(content, float) and math.isnan(content):
        return None
    
    if isinstance(content, str):
        content = content.strip()
        if content.lower() == "false":
            return False
        if content.lower() == "true":
            return True
        return content

    return content

@app.task(bind=True)
def exams_imports(self, user_id, csv_url):
    import traceback
    user = User.objects.get(pk=user_id)
    client = user.client

    importation = create_importation(user, csv_url)
    has_errors = False
    all_errors = []
    
    try:
        with transaction.atomic():
            csvreader = pd.read_csv(csv_url)
            for index, row in csvreader.iterrows():

                BASE_TEXT_LOCATION_CHOICES = {
                    'Textos base por questão': Exam.PER_QUESTION,
                    'Textos base por disciplina': Exam.SUBJECT_TOP,
                    'Textos base no início do caderno': Exam.EXAM_TOP,
                    'Textos base no final do caderno': Exam.EXAM_BOTTOM
                }
                
                name = clean_content(row.get('Título da avaliação', None))
                category = clean_content(row.get('Tipo de avaliação', Exam.EXAM))
                stage = clean_content(row.get('Etapa do ensino', None))
                system = clean_content(row.get('Sistema de ensino', None))
                grade = Decimal(clean_content(row.get('Nota geral do caderno', None))) if clean_content(row.get('Nota geral do caderno', None)) else None
                start_number = int(row.get('Qual número irá iniciar o caderno', 1))
                elaboration_deadline = clean_content(row.get('Prazo para elaboração', None))
                release_elaboration_teacher = clean_content(row.get('Data de liberação para professores', datetime.now().strftime('%d/%m/%Y')))
                unity_and_coordination = clean_content(row.get('Unidade e Coordenação', None))
                base_text_position = BASE_TEXT_LOCATION_CHOICES[clean_content(row.get('Onde serão mostrados os textos base', Exam.EXAM_TOP))]
                related_subjects = clean_content(row.get('Relacionar disciplinas', False))
                related_subjects_name = clean_content(row.get('Disciplinas relacionadas', None))
                random_questions = clean_content(row.get('Embaralhar questões', False))
                random_alternatives = clean_content(row.get('Embaralhar alternativas', False))
                show_ranking = clean_content(row.get('Mostrar ranking', False))
                group_files = clean_content(row.get('Agrupar anexos', False))
                allow_teacher_see = clean_content(row.get('Permitir correção/visualização por professores da mesma disciplina', False))
                orientations = clean_content(row.get('Orientações para a prova', None))
                existing_orientation = clean_content(row.get('Orientação existente', None))
                quantity_alternatives = clean_content(row.get('Limite de alternativas', None))
                deadline_for_review = clean_content(row.get('Data final para revisão', None))

                coordinations = []
                
                # validação nome unico

                if not unity_and_coordination:
                    raise SchoolCoordination.DoesNotExist()
                
                for _unity_and_coordination in unity_and_coordination.strip().split(','):
                    unity_name = _unity_and_coordination.split(' - ')[0]
                    coordination_name = " - ".join(_unity_and_coordination.split(' - ')[1:])

                    coordination = SchoolCoordination.objects.filter(
                        Q(
                            unity__name=unity_name.strip(),
                            name=coordination_name.strip(),
                            unity__client=client,
                        ),
                        Q(unity__educationsystem__name=system) if system else Q(),
                    ).first()

                    if not coordination:
                        raise SchoolCoordination.DoesNotExist()
                    
                    coordinations.append(coordination.id)

                if not is_exam_name_unique(coordinations, name):
                    raise ValueError(f"Já existe um caderno no ano de {datetime.now().year} com o nome '{name}'")
                                
                if existing_orientation:
                    existing_orientation = ExamOrientation.objects.filter(
                        title=existing_orientation,
                        user__coordination_member__coordination__unity__client=user.client
                    ).first()

                    if not existing_orientation:
                        raise ExamOrientation.DoesNotExist()

                    existing_orientation = existing_orientation.content
                
                exam = Exam.objects.create(
                    correction_by_subject=allow_teacher_see,
                    name=name,
                    status=Exam.ELABORATING,
                    random_alternatives=random_alternatives,
                    random_questions=random_questions,
                    elaboration_deadline=datetime.strptime(elaboration_deadline, "%d/%m/%Y"),
                    release_elaboration_teacher=datetime.strptime(release_elaboration_teacher, "%d/%m/%Y"),
                    category=Exam.EXAM if category == 'Prova' else Exam.HOMEWORK,
                    base_text_location=base_text_position,
                    start_number=start_number if start_number else 1,
                    total_grade=grade if grade else None,
                    show_ranking=show_ranking,
                    teaching_stage=TeachingStage.objects.get(
                        client=client,
                        name=stage
                    ) if stage else None,
                    education_system=EducationSystem.objects.get(
                        client=client,
                        name=system
                    ) if system else None,
                    orientations=existing_orientation if existing_orientation else (orientations if orientations else ""), 
                    related_subjects=related_subjects,
                    group_attachments=group_files,
                    quantity_alternatives=int(quantity_alternatives) if quantity_alternatives else None,
                    review_deadline=datetime.strptime(deadline_for_review, "%d/%m/%Y") if deadline_for_review else None,
                )

                exam.coordinations.set(
                    coordinations
                )
                
                if related_subjects:
                    if not related_subjects_name:
                        raise SubjectRelation.DoesNotExist()
                    
                    relations = SubjectRelation.objects.filter(
                        client=client,
                        name=related_subjects_name
                    )

                    if not relations:
                        raise SubjectRelation.DoesNotExist()
                    
                    exam.relations.set(
                        relations
                    )
        
    except Exception as e:
        print(traceback.format_exc())

        linha = index + 1
        
        has_errors = True

        if type(e) == SchoolCoordination.DoesNotExist:
        
            all_errors.append(f"Erro na linha {linha}: A coordenação não foi encontrada")

        elif type(e) == ExamOrientation.DoesNotExist:

            all_errors.append(f"Erro na linha {linha}: orientação existente não foi encontrada")

        elif type(e) == SubjectRelation.DoesNotExist:

            all_errors.append(f"Erro na linha {linha}: disciplina relacionada não foi encontrada")

        elif type(e) == TeachingStage.DoesNotExist:

            all_errors.append(f"Erro na linha {linha}: Etapa do ensino não foi encontrada")

        elif type(e) == EducationSystem.DoesNotExist:

            all_errors.append(f"Erro na linha {linha}: Sistema de ensino não foi encontrado")
        
        elif type(e) == KeyError:
            
            column_error_message = f'Erro na planilha, uma das colunas obrigatórias não foi encontrada - {e}'
            all_errors.append(column_error_message)
            
            importation.errors = all_errors
            importation.save()

            return column_error_message
        
        else:
            
            print('Erro desconhecido: ', e)
            all_errors.append(f"Erro na linha {linha}: {repr(e)}")
    
        importation.errors = all_errors
        importation.save()

    if has_errors:
        self.update_state(state=states.FAILURE)
        return "A importação foi finalizada mas retornou um erro."

    return  "Importação de instrumentos avaliativos finalizada com sucesso."

@app.task(bind=True)
def elaboration_request_import(self, user_id, csv_url, force_create_teacher_subject):

    user = User.objects.get(pk=user_id)

    importation = create_importation(user, csv_url, type=Import.ELABORATION_REQUEST)
    has_errors = False
    all_errors = []
    to_send_email = []

    try:
        csvreader = pd.read_csv(csv_url)

        exams = Exam.objects.filter(coordinations__in=user.get_coordinations_cache(), created_at__year=timezone.now().year).distinct()
        inspectors = Inspector.objects.filter(coordinations__in=user.get_coordinations_cache()).distinct()
        subjects = user.get_availables_subjects()
        teste = ""

        for index, row in csvreader.iterrows():

            exam_name = clean_content(row.get('Instrumento avaliativo'))
            grade_code = clean_content(row.get('Série'))
            subject = clean_content(row.get('Disciplina'))
            teacher_email = clean_content(row.get('Professor'))
            questions_quantity = clean_content(row.get('Quantidade de questões'))
            block_quantity_limit = clean_content(row.get('Limitar quantidade de questões inseridas', False))
            block_questions_quantity = clean_content(row.get('Definir quantidade de questões objetivas/discursivas', False))
            objective_quantity = clean_content(row.get('Quantidade de questões objetivas', 0))
            discursive_quantity = clean_content(row.get('Quantidade de questões discursivas', 0))
            block_subject_note = clean_content(row.get('Travar nota do professor', False))
            subject_note = clean_content(row.get('Nota da disciplina'))
            note = clean_content(row.get('Observação para o professor'))
            reviewers_emails = clean_content(row.get('Revisores', []))
            allow_teacher_give_grades = clean_content(row.get('Permitir que o professor distribua nota', False))
            
            grade = Grade.get_grade_by_code(code=grade_code)

            teacher = inspectors.get(
                Q(email__iexact=teacher_email) | Q(name__iexact=teacher_email)
            )

            args = subject.split(' - ')
            subject_name, knowledge_area = args[0].strip(), args[1].strip()

            if len(args) > 2:
                knowledge_area = f'{knowledge_area} - {args[2].strip()}'

            subject = subjects.filter(
                name__iexact=subject_name,
                knowledge_area__name__iexact=knowledge_area,
                knowledge_area__grades=grade,
            )
            if subject.count() > 1:
                if subject.filter(client__isnull=False).exists():
                    # uma disciplina
                    subject = subject.filter(client__isnull=False).first()
                else:
                    subject = subject.filter(client__isnull=True).first()
            else:
                subject = subject.first()

            if not subject:
                raise Subject.DoesNotExist()

            teacher_subject = TeacherSubject.objects.filter(
                teacher=teacher,
                subject=subject
            ).order_by('school_year').last()

            if not teacher_subject and force_create_teacher_subject:
                teacher_subject = TeacherSubject.objects.create(
                    teacher=teacher,
                    subject=subject,
                    school_year=timezone.now().year
                )

            if not teacher_subject:
                raise TeacherSubject.DoesNotExist()
            
            teacher_subject.refresh_from_db()
            
            exam = exams.get(name__iexact=exam_name)

            if ExamTeacherSubject.objects.using('default').filter(exam=exam, teacher_subject=teacher_subject).exists():
                continue

            biggest_order = (ExamTeacherSubject.objects.using('default').filter(exam=exam).aggregate(biggest=Max('order')).get('biggest') or 0) + 1

            if not allow_teacher_give_grades:
                allow_teacher_give_grades = False

            reviewers = []
            if reviewers_emails:
                reviewers_emails = reviewers_emails.split(',')
                reviewers = Inspector.objects.filter(
                    coordinations__in=user.get_coordinations_cache(),
                    email__in=reviewers_emails,
                ).distinct()

            exam_teacher_subject = ExamTeacherSubject.objects.create(
                teacher_subject=TeacherSubject.objects.using('default').get(pk=teacher_subject.pk),
                exam=exam,
                grade=grade,
                quantity=questions_quantity,
                note=note if note else "",
                order=biggest_order,
                subject_note=subject_note,
                block_subject_note=block_subject_note,
                block_quantity_limit=block_quantity_limit,
                block_questions_quantity=block_questions_quantity,
                objective_quantity=objective_quantity if objective_quantity else 0,
                discursive_quantity=discursive_quantity if discursive_quantity else 0,
                elaboration_email_sent=True,
                distribute_scores_freely=allow_teacher_give_grades,
            )

            if reviewers:
                exam_teacher_subject.reviewed_by.add(*reviewers)
            
            exam_teacher_subject.elaboration_email_sent = False
            exam_teacher_subject.save(skip_hooks=True)
            exam_teacher_subject.send_email_to_teacher()

    except Exception as e:

        linha = index + 1
        
        has_errors = True

        if isinstance(e, SchoolCoordination.DoesNotExist):
            all_errors.append(f"Erro na linha {linha}: A coordenação não foi encontrada")

        elif isinstance(e, Grade.DoesNotExist):
            all_errors.append(f"Erro na linha {linha}: A série não foi encontrada")

        elif isinstance(e, Exam.DoesNotExist):
            all_errors.append(f"Erro na linha {linha}: O instrumento avaliativo não foi encontrado")

        elif isinstance(e, Exam.MultipleObjectsReturned):
            all_errors.append(f"Erro na linha {linha}: Existe mais de um instrumento avaliativo com esse nome: {exam_name}")

        elif isinstance(e, Subject.DoesNotExist):
            all_errors.append(f"Erro na linha {linha}: A disciplina não foi encontrada")
        
        elif isinstance(e, Subject.MultipleObjectsReturned):
            all_errors.append(f"Erro na linha {linha}: Mais de uma disciplina com esses dados foi encontrada")

        elif isinstance(e, Inspector.DoesNotExist):
            all_errors.append(f"Erro na linha {linha}: O professor não existe")

        elif isinstance(e, TeacherSubject.DoesNotExist):
            all_errors.append(f"Erro na linha {linha}: O professor {teacher.name} não tem a disciplina {subject_name} #{force_create_teacher_subject} ## {teacher_subject} ### {teste}")

        elif isinstance(e, IntegrityError):
            all_errors.append(f"Erro na linha {linha}: Erro de integridade de dados {e}")

        elif isinstance(e, KeyError):
            column_error_message = f"Erro na planilha, uma das colunas obrigatórias não foi encontrada."
            all_errors.append(column_error_message)
            
            importation.errors = all_errors
            importation.save()

            return column_error_message
        
        else:
            print('Erro desconhecido: ', e)
            all_errors.append(f"Erro na linha {linha}: {repr(e)}")
    
        importation.errors = all_errors
        importation.save()

    if has_errors:
        self.update_state(state=states.FAILURE)
        return "A importação foi finalizada mas retornou um erro."

    return  "Importação de solicitações finalizada com sucesso."

@app.task(bind=True)
def essay_grades_import(self, user_id, csv_url):
    import traceback

    user = User.objects.get(pk=user_id)

    has_errors = False
    all_errors = []

    importation = create_importation(user, csv_url, type=Import.ESSAY_GRADES)

    question_weight = 1000

    competences = [
        "C1 - Norma Culta",
        "C2 - Tema e Tipo de Texto",
        "C3 - Arg. e Coerência",
        "C4 - Coesão",
        "C5 - Proposta de Intervenção"
    ]

    try:
        with transaction.atomic():
            csvreader = pd.read_csv(csv_url, index_col=False)
            for index, row in csvreader.iterrows():
                
                exam_name = clean_content(row.get('Título da avaliação', None))
                enrollment_number = clean_content(row.get('Matrícula', None))
                grade1 = clean_content(row.get('Nota C1', None))
                grade2 = clean_content(row.get('Nota C2', None))
                grade3 = clean_content(row.get('Nota C3', None))
                grade4 = clean_content(row.get('Nota C4', None))
                grade5 = clean_content(row.get('Nota C5', None))

                list_grades = [grade1, grade2, grade3, grade4, grade5]


                application_student = ApplicationStudent.objects.filter(
                    application__exam__name=exam_name,
                    student__enrollment_number=enrollment_number,
                ).first()

                if not application_student:
                    raise ApplicationStudent.DoesNotExist()

                application = application_student.application
                exam_question = application.exam.examquestion_set.availables(exclude_annuleds=True).filter(question__is_essay=True).first()

                nota = sum(list_grades)
                
                if not exam_question:
                    raise ExamQuestion.DoesNotExist()
                
                answer, _ = TextualAnswer.objects.get_or_create(
                    student_application=application_student,
                    question=exam_question.question,
                    defaults={
                        'grade': nota / question_weight,
                        'teacher_grade': nota,
                        'exam_question': exam_question,
                    }
                )

                for i, c in enumerate(competences):
                    criterio = CorrectionCriterion.objects.filter(
                        text_correction__name__icontains='Competências ENEM',
                        text_correction__client__isnull=True,
                        name=c
                    ).distinct().first()

                    CorrectionTextualAnswer.objects.update_or_create(
                        textual_answer=answer,
                        correction_criterion=criterio,
                        defaults={
                            'point': list_grades[i]
                        }
                    )

                application_student.is_omr = True
                application_student.save(skip_hooks=True)

    except Exception as e:
        print(traceback.format_exc())

        linha = int(index) + 1

        has_errors = True

        if type(e) == ApplicationStudent.DoesNotExist:
            all_errors.append(f"Erro na linha {linha}: O aluno não foi encontrado")

        elif type(e) == ExamQuestion.DoesNotExist:
            all_errors.append(f"Erro na linha {linha}: não foi possível encontrar a questão de redação do caderno {exam_name}")

        else:
            print('Erro desconhecido: ', e)
            all_errors.append(f"Erro na linha {linha}: {repr(e)}")

        importation.errors = all_errors
        importation.save()

    if has_errors:
        self.update_state(state=states.FAILURE)
        return "A importação foi finalizada mas retornou um erro."

    return  "Importação de notas de redação finalizada com sucesso."


            

    