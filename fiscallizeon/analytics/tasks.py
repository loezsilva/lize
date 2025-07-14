import io
import time
from datetime import timedelta

import pandas as pd
from celery import Task

import time
from django.core import management
from django.utils import timezone
from fiscallizeon.applications.models import Application, ApplicationStudent
from django_celery_beat.models import PeriodicTask

from fiscallizeon.exams.models import Exam 

from fiscallizeon.celery import app
from django.db.models import Q, F, Subquery, OuterRef, Count, Sum, Case, When, DateTimeField, Value
from fiscallizeon.analytics.management.commands import load_performance_by_date, load_performance_omr, generate_data_followup_dashboard, generate_data_followup_dashboard_cards, generate_data_followup_dashboard_questions
from fiscallizeon.students.models import Student
from fiscallizeon.clients.models import Unity
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.inspectors.models import Inspector, TeacherSubject
from fiscallizeon.accounts.models import User
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.exams.models import Exam, ExamQuestion, ExamTeacherSubject, StatusQuestion
from fiscallizeon.subjects.models import Subject


class CustomBaseTask(Task):
    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        if kwargs.get('delete_after_run', False) and status == 'SUCCESS':
            task = PeriodicTask.objects.get(name__icontains=kwargs['especific_exam_pk'])
            task.crontab.delete()
            
@app.task(base=CustomBaseTask)
def generate_student_performances_after_exam_finished(
        delete_after_run=False, 
        especific_exam_pk=None, 
        only_students=None,
        only_classes=None,
        only_bnccs=None,
        only_unities=None,
        only_subjects=None,
    ):
    
    start_time = time.time()
    now = timezone.now()
    yesterday = (now - timedelta(days=1)).date()
    message_message = f"******* O Processo de geração de performances foi fizalizado com sucesso e demorou: "
    
    
    if especific_exam_pk:
        exam = Exam.objects.get(pk=especific_exam_pk)
        exam.generate_performances(recalculate=True, only_students=only_students, only_classes=only_classes, only_bnccs=only_bnccs, only_unities=only_unities, only_subjects=only_subjects)
        
        return message_message + f"{time.time() - start_time} segundos *******"
    
    
    applications_student = ApplicationStudent.objects.annotate(
        update_needed=Case(
            When(
                Q(option_answers__updated_at__date__gte=yesterday),
                then=Value(True)
            ),
            When(
                Q(file_answers__updated_at__date__gte=yesterday),
                then=Value(True)
            ),
            When(
                Q(textual_answers__updated_at__date__gte=yesterday),
                then=Value(True)
            ),
            default=Value(False)
        )
    ).filter(
        update_needed=True
    ).distinct()

    exams = Exam.objects.filter(
        Q(
            Q(updated_at__date__gte=yesterday) | 
            Q(examquestion__updated_at__date__gte=yesterday) |
            Q(questions__updated_at__date__gte=yesterday) |
            Q(applicationstudent__in=applications_student) if applications_student else Q()
        )
    ).distinct()
    
    for exam in exams:
        exam.generate_performances(recalculate=True)
        
    return message_message + f"{time.time() - start_time} segundos *******"
    
@app.task
def generate_student_performances():
    try:
        management.call_command(load_performance_by_date.Command())
        management.call_command(load_performance_omr.Command())
    except Exception as e:
        print(e)
        
@app.task()
def generate_student_performances_after_finish_application(
        student_pk=None, 
    ):
    
    start_time = time.time()
    
    student = Student.objects.using('default').get(pk=student_pk)
    
    student.generate_performances_in_subjects(recalculate=True)
    student.generate_performances_in_bnccs(recalculate=True)
    
    if student.can_create_lists:
        student.create_lists()
    
    return f"Demorou {time.time() - start_time} segundos *******"

@app.task()
def generate_data_followup_dashboard_task(
        client_pk=None, 
    ):
    
    start_time = time.time()
    
    management.call_command(generate_data_followup_dashboard.Command(), client_pk=client_pk)
    
    return f"Demorou {time.time() - start_time} segundos *******"

@app.task()
def generate_data_exam_followup_task(
        exam_pk, 
        deadline,
        applications_pks,
    ):
    
    start_time = time.time()
    
    exam = Exam.objects.using('readonly2').get(pk=exam_pk)
    unities = Unity.objects.filter(pk__in=exam.coordinations.all().values('unity')).distinct()
    
    applications = Application.objects.using('readonly2').filter(pk__in=applications_pks)
    
    print("Gerando do caderno: ", exam.name)
    
    for unity in unities:

        classes = SchoolClass.objects.using('readonly2').filter(
            pk__in=applications.filter(exam=exam, applicationstudent__student__classes__coordination__unity=unity).values_list('applicationstudent__student__classes', flat=True),
            coordination__unity=unity,
            school_year=exam.created_at.year,
            temporary_class=False,
        ).distinct()
        
        for classe in classes:
            
            quantities = exam.get_answers_awaiting_response(school_class=classe)
            
            inspectors = Inspector.objects.filter(
                teachersubject__classes=classe,
                teachersubject__subject__in=exam.examteachersubject_set.values('teacher_subject__subject'),
            ).distinct()

            performance_classe = exam.performances_followup.filter(
                deadline=deadline, 
                school_class=classe, 
                unity=unity, 
                coordination=classe.coordination,
            ).last()

            if performance_classe:
                performance_classe.objective_quantity = quantities['objective_quantity']
                performance_classe.objective_total = quantities['objective_total']
                
                performance_classe.discursive_quantity = quantities['discursive_quantity']
                performance_classe.discursive_total = quantities['discursive_total']
                
                performance_classe.quantity = quantities['objective_quantity'] + quantities['discursive_quantity']
                performance_classe.total = quantities['objective_total'] + quantities['discursive_total']
                
                performance_classe.save()
                
            else:
                performance_classe = exam.performances_followup.create(
                    deadline=deadline,
                    unity=unity,
                    coordination=classe.coordination,
                    school_class=classe,
                    objective_quantity=quantities['objective_quantity'],
                    objective_total=quantities['objective_total'],
                    discursive_quantity=quantities['discursive_quantity'],
                    discursive_total=quantities['discursive_total'],
                    quantity=quantities['objective_quantity'] + quantities['discursive_quantity'],
                    total=quantities['objective_total'] + quantities['discursive_total']
                )
                
            performance_classe.inspectors.set(inspectors)
            performance_classe.objective_examquestions.set(quantities['objective_examquestions_pks'])
            performance_classe.discursive_examquestions.set(quantities['discursive_examquestions_pks'])
    
    return f"Demorou {time.time() - start_time} segundos *******"

@app.task()
def generate_data_exam_followup_cards_task(exam_pk):
    start_time = time.time()
    management.call_command(generate_data_followup_dashboard_cards.Command(), exam_pk=exam_pk)
    return f"Demorou {time.time() - start_time} segundos *******"

@app.task()
def generate_data_exam_followup_questions_task(exam_pk):
    start_time = time.time()
    management.call_command(generate_data_followup_dashboard_questions.Command(), exam_pk=exam_pk)
    return f"Demorou {time.time() - start_time} segundos *******"


#Exportação dash administrativo
def get_questions_df(questions):
    status_dict = {
        'approved': 'Aprovadas',
        'reproved': 'Reprovadas',
        'correction_pending': 'Correção sugerida',
        'use_later': 'Usar depois',
        'annuled': 'Anuladas',
        'lates': 'Atrasadas',
        'opened': 'Em aberto'
    }

    df = pd.DataFrame({'Status': list(questions.keys())[1:], 'Quantidade': list(questions.values())[1:]})
    df['Porcentagem'] = (df['Quantidade'] / questions['count']) * 100
    df['Porcentagem'] = df['Porcentagem'].round(2)
    df['Status'] = df['Status'].map(status_dict)
    return df

def get_exams_df(exams):
    status_dict = {
        'elaborating': 'Elaborando',
        'opened': 'Abertos',
        'closed': 'Fechados',
        'send_review': 'Em revisão',
        'text_review': 'Revisão de texto',
        'is_printed_count': 'Impressos',
        'late': 'Atrasados'
    }

    df = pd.DataFrame({'Status': list(exams.keys())[1:], 'Quantidade': list(exams.values())[1:]})
    df['Porcentagem'] = (df['Quantidade'] / exams['count']) * 100
    df['Porcentagem'] = df['Porcentagem'].round(2)
    df['Status'] = df['Status'].map(status_dict)
    return df

def get_teacher_df(user, teachers, subjects, teaching_stages, 
                   education_systems, year, segments, initial_date, final_date):
    
    exam_questions = ExamQuestion.objects.filter(
        Q(exam_teacher_subject__teacher_subject__subject__in=subjects) if subjects else Q(),
        Q(exam_teacher_subject__teacher_subject__teacher__in=teachers) if teachers else Q(),
        Q(created_at__year=year) if year else Q(),
        Q(exam_teacher_subject__created_at__gte=initial_date) if initial_date else Q(),
        Q(exam_teacher_subject__created_at__lte=final_date) if final_date else Q(),
        Q(exam_teacher_subject__grade__level__in=segments) if segments else Q(),
    ).exclude(is_abstract=True).distinct()

    teachers = Inspector.objects.filter(
        Q(coordinations__in=user.get_coordinations_cache()),
        Q(pk__in=teachers) if teachers else Q(),
        Q(teachersubject__subject__in=subjects) if subjects else Q(),
        Q(teachersubject__examteachersubject__grade__level__in=segments) if segments else Q(),
    ).annotate(
        questions_count=Count('teachersubject__examteachersubject__examquestion', filter=Q(
            Q(teachersubject__examteachersubject__examquestion__is_abstract=False),
            Q(teachersubject__examteachersubject__examquestion__created_at__year=year) if year else Q(),
            Q(teachersubject__examteachersubject__examquestion__exam_teacher_subject__grade__level__in=segments) if segments else Q(),
            Q(teachersubject__examteachersubject__examquestion__exam_teacher_subject__teacher_subject__subject__in=subjects) if subjects else Q(),
        ), distinct=True)
    ).order_by('-questions_count', 'name').distinct()

    teachers = teachers.annotate(
        questions_count=Count('teachersubject__examteachersubject__examquestion', distinct=True)
    ).order_by('-questions_count', 'name').distinct()
    
    teachers_data = []    
    for teacher in teachers:
        exam_teacher_subjects = ExamTeacherSubject.objects.filter(teacher_subject__teacher=teacher).distinct()
        
        exam_questions = ExamQuestion.objects.filter(
            Q(exam_teacher_subject__in=exam_teacher_subjects),
            Q(exam__teaching_stage__in=teaching_stages) if teaching_stages else Q(),
            Q(exam__education_system__in=education_systems) if education_systems else Q(),
            Q(exam_teacher_subject__grade__level__in=segments) if segments else Q(),
            Q(statusquestion__created_at__gte=initial_date) if initial_date else Q(),
            Q(statusquestion__created_at__lte=final_date) if final_date else Q(),
        ).exclude(is_abstract=True).distinct()
        
        common_filters_statusquestion = Q(
            Q(statusquestion__created_at__year=year) if year else Q(),
            Q(statusquestion__active=True),
        )
        
        data = {
            "name": teacher.__str__(),
            "id": teacher.pk,
            "questions": {
                "approved": exam_questions.filter(common_filters_statusquestion, Q(statusquestion__status=StatusQuestion.APPROVED)).distinct().count(),
                "reproved": exam_questions.filter(common_filters_statusquestion, Q(statusquestion__status=StatusQuestion.REPROVED)).distinct().count(),
                "correction_pending": exam_questions.filter(common_filters_statusquestion, Q(statusquestion__status=StatusQuestion.CORRECTION_PENDING)).distinct().count(),
                "use_later": exam_questions.filter(common_filters_statusquestion, Q(statusquestion__status=StatusQuestion.USE_LATER)).distinct().count(),
                "corrected": exam_questions.filter(common_filters_statusquestion, Q(statusquestion__status=StatusQuestion.CORRECTED)).distinct().count(),
                "annuled": exam_questions.filter(common_filters_statusquestion, Q(statusquestion__status=StatusQuestion.ANNULLED)).distinct().count(),
                "seen": exam_questions.filter(Q(statusquestion__created_at__year=year) if year else Q(), Q(statusquestion__status=StatusQuestion.SEEN)).distinct().count(),
                "lates": exam_questions.filter(Q(created_at__year=year) if year else Q(), Q(is_late=True)).distinct().count(),
                "count": exam_questions.filter(Q(created_at__year=year) if year else Q()).count(),
            }
        }
        teachers_data.append(data)

    df = pd.DataFrame([t["questions"] for t in teachers_data], index=[t["name"] for t in teachers_data])
    df.columns = ['Aprovadas', 'Reprovadas', 'Correção sugerida', 'Usar depois', 'Corrigidas', 'Anuladas', 'Vistas', 'Atrasadas', 'Total']
    return df

def get_subjects_df(user, teachers, subjects, teaching_stages, 
                    education_systems, year, segments, initial_date, final_date):
    
    exams = Exam.objects.filter(
        Q(coordinations__in=user.get_coordinations_cache()),
        Q(teaching_stage__in=teaching_stages) if teaching_stages else Q(),
        Q(education_system__in=education_systems) if education_systems else Q(),
        Q(created_at__year=year) if year else Q(),
        Q(created_at__gte=initial_date) if initial_date else Q(),
        Q(created_at__lte=final_date) if final_date else Q(),
        Q(examteachersubject__grade__level__in=segments) if segments else Q(),
    ).annotate(
        tmt_start_time=Case(
            When(
                Q(release_elaboration_teacher__isnull=False),
                then=F('release_elaboration_teacher')
            ),
            default=Subquery(ExamQuestion.objects.filter(exam__pk=OuterRef('pk')).order_by('created_at').values('created_at')[:1]),
            output_field=DateTimeField()
        ),
        end_time=Subquery(ExamQuestion.objects.filter(exam__pk=OuterRef('pk')).order_by('-created_at').values('created_at')[:1]),
    ).exclude(is_abstract=True).distinct()
    
    teacher_subjects = TeacherSubject.objects.filter(
        Q(examteachersubject__exam__in=exams),
        Q(teacher__in=teachers) if teachers else Q(),
        Q(subject__in=subjects) if subjects else Q(),
        Q(examteachersubject__grade__level__in=segments) if segments else Q(),
    ).distinct()
    
    # if self.request.GET.get('only_lates'): 
    #     subject_id = self.request.GET.get('subject_id')
    #     if not subject_id:
    #         raise Exception('É necessário indicar qual a disciplina através do parametro: subject_id')
        
    #     try:
    #         filtred_exams = exams.filter(
    #             Q(teacher_subjects__subject__id=subject_id),
    #             Q(teacher_subjects__in=teacher_subjects),
    #         ).annotate(
    #             lates=Exists(
    #                 ExamQuestion.objects.filter(
    #                     exam_teacher_subject__teacher_subject__subject=subject_id,
    #                     exam__pk=OuterRef('pk'), 
    #                     created_at__gt=OuterRef('elaboration_deadline')
    #                 ).distinct().exclude(is_abstract=True)
    #             ),
    #         ).distinct()
            
    #     except Exception as e:
    #         raise Exception('Não foi possível encontrar a disciplina informada')
        
    #     return filtred_exams.filter(lates=True).count()
    
    subjects = Subject.objects.filter(
        Q(teachersubject__examteachersubject__exam__in=exams),
        Q(teachersubject__subject__in=subjects) if subjects else Q(),
        Q(teachersubject__in=teacher_subjects),
    ).annotate(
        questions_count=Count('teachersubject__examteachersubject__exam__examquestion', distinct=True),
    ).order_by('-questions_count').distinct()

    subjects_data = []
    
    for subject in subjects:
        exam_questions = ExamQuestion.objects.filter(
            Q(exam__in=exams),
            Q(exam_teacher_subject__teacher_subject__subject=subject),
            Q(exam_teacher_subject__teacher_subject__in=teacher_subjects),
            Q(exam_teacher_subject__grade__level__in=segments) if segments else Q(),
            Q(created_at__year=year) if year else Q()
        ).exclude(is_abstract=True).distinct()
        
        exam_questions_aggregations = exam_questions.annotate(
            approveds=Count(
                Subquery(
                    StatusQuestion.objects
                    .filter(
                        Q(created_at__gte=initial_date) if initial_date else Q(),
                        Q(created_at__lte=final_date) if final_date else Q(),
                        exam_question__pk=OuterRef('pk'),
                        status=StatusQuestion.APPROVED,
                        active=True
                    )
                    .order_by('-updated_at')
                    .values('pk')[:1]
                ),
                distinct=True
            ),
            reproveds=Count(
                Subquery(
                    StatusQuestion.objects
                    .filter(
                        Q(updated_at__gte=initial_date) if initial_date else Q(),
                        Q(updated_at__lte=final_date) if final_date else Q(),
                        exam_question__pk=OuterRef('pk'),
                        status=StatusQuestion.REPROVED,
                        active=True
                    )
                    .order_by('-updated_at')
                    .values('pk')[:1]
                ),
                distinct=True
            ),
            correction_pendings=Count(
                Subquery(
                    StatusQuestion.objects
                    .filter(
                        Q(updated_at__gte=initial_date) if initial_date else Q(),
                        Q(updated_at__lte=final_date) if final_date else Q(),
                        exam_question__pk=OuterRef('pk'),
                        status=StatusQuestion.CORRECTION_PENDING,
                        active=True
                    )
                    .order_by('-updated_at')
                    .values('pk')[:1]
                ),
                distinct=True
            ),
            correcteds=Count(
                Subquery(
                    StatusQuestion.objects
                    .filter(
                        Q(updated_at__gte=initial_date) if initial_date else Q(),
                        Q(updated_at__lte=final_date) if final_date else Q(),
                        exam_question__pk=OuterRef('pk'),
                        status=StatusQuestion.CORRECTED,
                        active=True
                    )
                    .order_by('-updated_at')
                    .values('pk')[:1]
                ),
                distinct=True
            ),
            annuleds=Count(
                Subquery(
                    StatusQuestion.objects
                    .filter(
                        Q(updated_at__gte=initial_date) if initial_date else Q(),
                        Q(updated_at__lte=final_date) if final_date else Q(),
                        exam_question__pk=OuterRef('pk'),
                        status=StatusQuestion.ANNULLED,
                        active=True
                    )
                    .order_by('-updated_at')
                    .values('pk')[:1]
                ),
                distinct=True
            ),
        ).aggregate(
            Sum('approveds'),
            Sum('reproveds'),
            Sum('correction_pendings'),
            Sum('correcteds'),
            Sum('annuleds'),
        )
        
        data = {
            "name": subject.__str__(),
            "questions": {
                "opened": exam_questions.filter(
                    Q(
                        Q(statusquestion__isnull=True) | 
                        Q(statusquestion__status=StatusQuestion.SEEN)
                    )
                ).count(),
                "approved": exam_questions_aggregations.get('approveds__sum') or 0,
                "reproved": exam_questions_aggregations.get('reproveds__sum') or 0,
                "correction_pending": exam_questions_aggregations.get('correction_pendings__sum') or 0,
                "corrected": exam_questions_aggregations.get('correcteds__sum') or 0,
                "annuled": exam_questions_aggregations.get('annuleds__sum') or 0,
                "lates": exam_questions.filter(created_at__gt=F('exam__elaboration_deadline')).distinct().count(),
                "count": exam_questions.count(),
            }
        }
        subjects_data.append(data)

    df = pd.DataFrame([s["questions"] for s in subjects_data], index=[s["name"] for s in subjects_data])
    df.columns = ['Abertas', 'Aprovadas', 'Reprovadas', 'Correção sugerida', 'Corrigidas', 'Anuladas', 'Atrasadas', 'Total']
    return df


@app.task(bind=True)
def export_admin_dashboard(self, user_pk, questions, exams, teachers, subjects, teaching_stages, 
                           education_systems, year, segments, initial_date, final_date):
    
    self.update_state(state='PROGRESS')
    user = User.objects.get(pk=user_pk)
    questions_df = get_questions_df(questions)
    exams_df = get_exams_df(exams)

    args = [user, teachers, subjects, teaching_stages, 
            education_systems, year, segments, initial_date, 
            final_date]

    teachers_df = get_teacher_df(*args)
    subjects_df = get_subjects_df(*args)
    
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        questions_df.to_excel(writer, sheet_name='Questões', index=False)
        exams_df.to_excel(writer, sheet_name='Cadernos', index=False)
        teachers_df.to_excel(writer, sheet_name='Professores')
        subjects_df.to_excel(writer, sheet_name='Disciplinas')

    buffer.seek(0)
    fs = PrivateMediaStorage()
    filename = fs.save(f'devolutivas/dash-admininistrativo/administrativo_{int(time.time())}.xlsx', buffer)
    self.update_state(state='SUCCESS', meta=fs.url(filename))