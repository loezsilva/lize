from django.core.management.base import BaseCommand
import polars as pl
import os, time, math
from decouple import config
from fiscallizeon.answers.models import FileAnswer, TextualAnswer, OptionAnswer, SumAnswer
from fiscallizeon.exams.models import ExamQuestion, Exam, TeacherSubject, ExamTeacherSubject, StatusQuestion
from fiscallizeon.questions.models import Question
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.students.models import Student
from fiscallizeon.subjects.models import Subject
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.omr.models import OMRStudents, OMRDiscursiveScan

from django.db.models import F, When, Case, DateTimeField, Value, Q, Subquery, OuterRef, DecimalField, Sum, Count, Exists, BooleanField, UUIDField
from django.db.models.functions import Coalesce, Concat
from django.db import connection
from django.utils import timezone
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.clients.models import Client
from fiscallizeon.integrations.models import SubjectCode
import os

LINES_PER_PAGE = 30 # Esse número precisa ser validado

def get_query(query):
    sql_query, params = query.sql_with_params()

    # Formatar a consulta SQL corretamente com os parâmetros
    with connection.cursor() as cursor:
        formatted_sql_query = cursor.mogrify(sql_query, params).decode('utf-8')

    return formatted_sql_query

class Command(BaseCommand):
    help = 'Command para carregar gerar dataframes dos dashboard v2'

    def add_arguments(self, parser):
        parser.add_argument('--clients', default=None)
        parser.add_argument('--exclude_clients', default=None)
        parser.add_argument('--year', type=int, default=timezone.now().year)
        parser.add_argument('--inclemental', type=bool, default=False)
        
    def handle(self, *args, **kwargs):

        clients_list = kwargs['clients'].split(',') if kwargs['clients'] else []
        exclude_clients_list = kwargs['exclude_clients'].split(',') if kwargs['exclude_clients'] else []
        self.start_time = time.time()
        self.year = kwargs['year']
        self.inclemental = kwargs['inclemental']
        self.uri = config('DATABASE_URL_READONLY2')
        
        clients = (
            Client.objects.using('readonly2').filter(
                Q(status__in=[Client.ACTIVED, Client.IN_POC]),
                Q(id__in=clients_list) if len(clients_list) else Q(), # Filtrar um cliente específico caso necessário
                Q(
                    Q(has_dashboards=True) | 
                    Q(unities__coordinations__members__user__user_permissions__codename='view_dashboards')
                )
            )
            .exclude(
                Q(id__in=exclude_clients_list) if len(exclude_clients_list) else Q()
            )
            .distinct()
        )
        
        for client in clients:
            try:
                self.client = str(client.id)
                self.save_path = f'tmp/dashboards/{self.client}/performances'
                os.makedirs(f'{self.save_path}/', exist_ok=True)
                
                self.create_subjects_data(filename='subjects')
                self.create_exam_questions_data(filename='exam_questions')
                self.create_exams_data(filename='exams')
                self.create_exams_teacher_subject_data(filename='exam_teacher_subjects')
                self.create_students_data(filename='students')
                self.create_applications_data(filename='applications')
                self.create_applications_student_data(filename='applications_student')
                self.create_teachers_data(filename='teachers')                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        
                self.create_bnccs_data(filename='bnccs')
                
                # Dataframe mais demorado para gerar
                self.create_answers_data(filename='real_answers')
                time.sleep(5)
                self.create_fake_answers_data(filename='fake_answers')
                time.sleep(5)
                self.answers_union(filename='answers') # Desacoplei essa função para economizar memória...

                client.last_generation_dashboard = timezone.now()
                client.save(skip_hooks=True)
                
            except Exception as e:
                print("########## >>>", client.name)
                print(e)

        print(f"no geral demorou: {time.time() - self.start_time}")

    def create_subjects_data(self, filename):

        query_subjects = Subject.objects.using('readonly2').annotate(
            subject_code=Subquery(
                SubjectCode.objects.filter(
                    client=self.client,
                    subject=OuterRef('id')
                ).values('code')[:1]
            ),
            subject_name=Case(
                When(
                    subject_code__isnull=False,
                    then=Concat(
                        F('subject_code'),
                        Value(' - '),
                        F('knowledge_area__name'),
                    )
                ), default=Concat(
                    F('name'),
                    Value(' - '),
                    F('knowledge_area__name'),
                ),
            )
        ).values(
            'id',
            'subject_name',
        ).distinct().query


        df = pl.read_database_uri(query=get_query(query_subjects), uri=self.uri).rename({ 'id': 'subject_id' }).select('subject_id', 'subject_name')
        
        df = df.unique()
        
        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo
        df.write_csv(f'{self.save_path}/{filename}.csv') # Salva em arquivo
        print(f"{'-' * 20} Terminou {filename} em {time.time() - self.start_time} {'-' * 20}")
        print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")

    def create_exam_questions_data(self, filename):
        exam_questions = ExamQuestion.objects.using('readonly2').filter(
            updated_at__date__year__gte=self.year,
            question__is_essay=False,
        ).annotate(
            teacher_id=F('exam_teacher_subject__teacher_subject__teacher'),
            exam_teacher_subject_order=F('exam_teacher_subject__order'),
            question_category=F('question__category'),
            quantity_lines=F('question__quantity_lines'),
            topics_percent=Case(
                When(
                    condition=Q(
                        question__topics__isnull=False
                    ), then=Value(100 / 4)
                ), default=Value(0.0)
            ),
            abilities_percent=Case(
                When(
                    condition=Q(
                        question__abilities__isnull=False
                    ), then=Value(100 / 4)
                ), default=Value(0.0)
            ),
            competences_percent=Case(
                When(
                    condition=Q(
                        question__competences__isnull=False
                    ), then=Value(100 / 4)
                ), default=Value(0.0)
            ),
            level_percent=Case(
                When(
                    condition=~Q(
                        question__level=Question.UNDEFINED
                    ), then=Value(100 / 4)
                ), default=Value(0.0)
            ),
            quality=F('topics_percent') + F('abilities_percent') + F('competences_percent') + F('level_percent'),
            subject=Case(
                When(
                    condition=Q(exam__is_abstract=True),
                    then=Subquery(
                        ExamQuestion.objects.using('readonly2').filter(
                            question=OuterRef('question'),
                            exam=OuterRef('exam')
                        ).values('question__subject')[:1]
                    ),
                ),
                default=Subquery(
                    ExamQuestion.objects.using('readonly2').filter(
                        question=OuterRef('question'),
                        exam=OuterRef('exam')
                    ).values('exam_teacher_subject__teacher_subject__subject')[:1]
                ),
            ),
            status=Subquery(
                StatusQuestion.objects.using('readonly2').filter(
                    Q(
                        exam_question=OuterRef('pk'),
                        active=True,
                    ),
                    ~Q(status=StatusQuestion.SEEN)
                ).values('status')[:1]
            ),
            late=Case(
                When(
                    condition=Q(
                        exam__elaboration_deadline__lt=timezone.now()
                    ),
                    then=Exists(
                        StatusQuestion.objects.using('readonly2').filter(
                            Q(
                                exam_question=OuterRef('pk'),
                                active=True,
                            ),
                            Q(status__in=StatusQuestion.get_unavailables_status())
                        )
                    )
                ),
                default=Value(False),
                output_field=BooleanField()
            ),
        )

        query_exam_questions = exam_questions.annotate(
            is_available=Value(False),
        ).values(
            'id',
            'exam_id',
            'teacher_id',
            'question',
            'question_category',
            'weight',
            'is_available',
            'quantity_lines',
            'subject',
            'quality',
            'status',
            'late',
            'is_abstract',
            'order',
            'exam_teacher_subject_order',
        ).query

        query_exam_questions_availables = exam_questions.availables(
            exclude_annuleds=True
        ).annotate(
            is_available=Value(True)
        ).values(
            'id',
            'exam_id',
            'teacher_id',
            'question',
            'question_category',
            'weight',
            'is_available',
            'quantity_lines',
            'subject',
            'quality',
            'status',
            'late',
            'is_abstract',
            'order',
            'exam_teacher_subject_order',
        ).query
        
        df_exam_questions = pl.read_database_uri(query=get_query(query_exam_questions), uri=self.uri).rename({'subject': 'subject_id'}).select(
            'id',
            'exam_id',
            'teacher_id',
            'question_id',
            'question_category',
            'weight',
            'is_available',
            'quantity_lines',
            'subject_id',
            'quality',
            'status',
            'late',
            'is_abstract',
            'order',
            'exam_teacher_subject_order',
        )

        df_exam_questions_availables = pl.read_database_uri(query=get_query(query_exam_questions_availables), uri=self.uri).rename({'subject': 'subject_id'}).select(
            'id',
            'exam_id',
            'teacher_id',
            'question_id',
            'question_category',
            'weight',
            'is_available',
            'quantity_lines',
            'subject_id',
            'quality',
            'status',
            'late',
            'is_abstract',
            'order',
            'exam_teacher_subject_order',
        )

        df_all = df_exam_questions.join(df_exam_questions_availables, on=['exam_id', 'question_id'], how='anti')

        df = df_all.vstack(df_exam_questions_availables)
        
        df = df.with_columns(
            pl.col('status').fill_null(StatusQuestion.OPENED).fill_nan(StatusQuestion.OPENED)
        ).select(
            'id',
            'exam_id',
            'teacher_id',
            'question_id',
            'question_category',
            'weight',
            'is_available',
            'quantity_lines',
            'subject_id',
            'quality',
            'status',
            'late',
            'is_abstract',
            'order',
            'exam_teacher_subject_order',
        )
        
        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo

        print(f"{'-' * 20} Terminou {filename} em {time.time() - self.start_time} {'-' * 20}")
        print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")
    
    def create_exams_data(self, filename):
        query_exams = Exam.objects.using('readonly2').filter(
            created_at__date__year__gte=self.year,
            coordinations__unity__client=self.client,
        ).annotate(
            exam_id=F('pk'),
            total_solicitation=Subquery(
                ExamTeacherSubject.objects.using('readonly2').filter(
                    exam=OuterRef('pk')
                ).values('exam').annotate(Sum('quantity')).values_list('quantity__sum')[:1]
            ),
            exam_name=F('name'),
            teacher_id=F('teacher_subjects__teacher__id'),
            teacher_name=F('teacher_subjects__teacher__name'),
            teaching_stage_name=F('teaching_stage__name'),
            education_system_name=F('education_system__name'),
        ).values(
            'exam_id',
            'exam_name',
            'elaboration_deadline',
            'total_solicitation',
            'coordinations__unity',
            'coordinations__unity__name',
            'teacher_id',
            'teacher_name',
            'status',
            'teaching_stage',
            'teaching_stage_name',
            'education_system',
            'education_system_name',
            'is_english_spanish',
        ).distinct().query

        try:

            df = (
                pl.read_database_uri(query=get_query(query_exams), uri=self.uri)
                .rename({
                    'name': 'unity_name',
                    'is_english_spanish': 'is_foreign_language',
                })
            )

            df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo


            print(f"{'-' * 20} Terminou {filename} em {time.time() - self.start_time} {'-' * 20}")
            print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")

        except Exception as e:
            print("Erro em create_exams_data:", e)
    
    def create_exams_teacher_subject_data(self, filename):
        
        query_exam_teacher_subjects = ExamTeacherSubject.objects.using('readonly2').filter(
            # teacher_subject__active=True,
            exam__coordinations__unity__client=self.client,
        ).annotate(
            questions_count=Subquery(
                ExamQuestion.objects.using('readonly2').filter(
                    Q(exam_teacher_subject=OuterRef('pk')),
                    Q(
                        Q(
                            statusquestion__isnull=True
                        ) |
                        Q(
                            Q(statusquestion__active=True),
                            ~Q(statusquestion__status__in=StatusQuestion.get_unavailables_status()),
                        )
                    ),
                ).values('exam_teacher_subject').annotate(
                    total=Count('pk')
                ).values('total')[:1]
            ),
            soliciteds=F('quantity'),
            exam_name=F('exam__name'),
            teacher_name=F('teacher_subject__teacher__name'),
            teaching_stage_name=F('exam__teaching_stage__name'),
            education_system_name=F('exam__education_system__name'),
        ).values(
            'id',
            'exam',
            'exam_name',
            'teacher_subject__teacher',
            'teacher_subject__subject',
            'teacher_name',
            'exam__elaboration_deadline',
            'exam__coordinations__unity',
            'exam__coordinations__unity__name',
            'exam__teaching_stage',
            'teaching_stage_name',
            'exam__education_system',
            'education_system_name',
            'soliciteds',
            'questions_count',
        ).query

        try:

            df = (
                pl.read_database_uri(query=get_query(query_exam_teacher_subjects), uri=self.uri)
                .rename({
                    'id': 'exam_teacher_subject',
                    'name': 'unity_name'
                }).with_columns(
                    pl.col('questions_count').fill_null(0).fill_nan(0)
                )
                .select(
                    'exam_teacher_subject', 
                    'exam_id', 
                    'exam_name', 
                    'soliciteds', 
                    'questions_count', 
                    'teacher_id', 
                    'subject_id', 
                    'teacher_name', 
                    'elaboration_deadline', 
                    'unity_id', 
                    'unity_name', 
                    'teaching_stage_id', 
                    'teaching_stage_name', 
                    'education_system_id',
                    'education_system_name',
                )
            )
            
            df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo

            print(f"{'-' * 20} Terminou {filename} em {time.time() - self.start_time} {'-' * 20}")
            print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")

        except Exception as e:
            print("Erro em create_exams_teacher_subject_data:", e)
    
    def create_answers_data(self, filename):

        def common_annotations(type='discursive'):   
            
            annotations = {}

            if type == 'discursive':
                question_annotation = F('question')
                question_category_annotation = F('question__category')
                grade_annotation = Coalesce(F('teacher_grade'), Value(0), output_field=DecimalField())
                answered_annotation = Case(
                    When(
                        condition=Q(
                            teacher_grade__isnull=False,
                        ), then=Value(True),
                    ), default=Value(False)
                )
                question_weight_annotation = Coalesce(
                    Subquery(
                        ExamQuestion.objects.using('readonly2').filter(
                            question=OuterRef('question'),
                            exam=OuterRef('student_application__application__exam')
                        ).values('weight')[:1]
                    ),
                    Value(0),
                    output_field=DecimalField()
                )
                hit_annotation = Case(
                    When(
                        condition=Q(grade__gte=F('question_weight')), 
                        then=Value(True)
                    ),
                    default=Value(False)
                )
                subject_id_annotation = Case(
                    When(
                        condition=Q(student_application__application__exam__is_abstract=True), 
                        then=F('question__subject_id')
                    ),
                    default=Subquery(
                        ExamQuestion.objects.using('readonly2').filter(
                            question=OuterRef('question'),
                            exam=OuterRef('student_application__application__exam')
                        ).values('exam_teacher_subject__teacher_subject__subject_id')[:1]
                    ), output_field=UUIDField()
                )
                
                subject_name_annotation = Case(
                    When(
                        condition=Q(student_application__application__exam__is_abstract=True), 
                        then=F('question__subject__name')
                    ),
                    default=Subquery(
                        ExamQuestion.objects.using('readonly2').filter(
                            question=OuterRef('question'),
                            exam=OuterRef('student_application__application__exam')
                        ).values('exam_teacher_subject__teacher_subject__subject__name')[:1]
                    )
                )
            
            elif type == 'choice':
                question_annotation = F('question_option__question')
                question_category_annotation = F('question_option__question__category')
                grade_annotation = Coalesce(
                    Case(
                        When(
                            condition=Q(question_option__is_correct=True),
                            then=Subquery(
                                ExamQuestion.objects.using('readonly2').filter(
                                    question=OuterRef('question_option__question'),
                                    exam=OuterRef('student_application__application__exam')
                                ).values('weight')[:1]
                            ),
                        ), default=Value(0),
                        output_field=DecimalField()
                    ),
                    Value(0),
                    output_field=DecimalField()
                )
                answered_annotation = Value(True)
                question_weight_annotation = Coalesce(
                    Subquery(
                        ExamQuestion.objects.using('readonly2').filter(
                            question=OuterRef('question_option__question'),
                            exam=OuterRef('student_application__application__exam')
                        ).values('weight')[:1]
                    ),
                    Value(0),
                    output_field=DecimalField()
                )
                hit_annotation = Case(
                    When(
                        condition=Q(question_option__is_correct=True), 
                        then=Value(True)
                    ),
                    default=Value(False)
                )
                subject_id_annotation = Case(
                    When(
                        condition=Q(student_application__application__exam__is_abstract=True), 
                        then=F('question_option__question__subject_id')
                    ),
                    default=Subquery(
                        ExamQuestion.objects.using('readonly2').filter(
                            question=OuterRef('question_option__question'),
                            exam=OuterRef('student_application__application__exam')
                        ).values('exam_teacher_subject__teacher_subject__subject_id')[:1]
                    ), output_field=UUIDField()
                )
                subject_name_annotation = Case(
                    When(
                        condition=Q(student_application__application__exam__is_abstract=True), 
                        then=F('question_option__question__subject__name')
                    ),
                    default=Subquery(
                        ExamQuestion.objects.using('readonly2').filter(
                            question=OuterRef('question_option__question'),
                            exam=OuterRef('student_application__application__exam')
                        ).values('exam_teacher_subject__teacher_subject__subject__name')[:1]
                    )
                )

            elif type == 'sum':
                question_annotation = F('question')
                question_category_annotation = F('question__category')
                answered_annotation = Value(True)
                question_weight_annotation = Coalesce(
                    Subquery(
                        ExamQuestion.objects.using('readonly2').filter(
                            question=OuterRef('question'),
                            exam=OuterRef('student_application__application__exam')
                        ).values('weight')[:1]
                    ),
                    Value(0),
                    output_field=DecimalField()
                )
                hit_annotation = Case(
                    When(
                        condition=Q(grade__gte=F('question_weight')), 
                        then=Value(True)
                    ),
                    default=Value(False)
                )
                subject_id_annotation = Case(
                    When(
                        condition=Q(student_application__application__exam__is_abstract=True), 
                        then=F('question__subject_id')
                    ),
                    default=Subquery(
                        ExamQuestion.objects.using('readonly2').filter(
                            question=OuterRef('question'),
                            exam=OuterRef('student_application__application__exam')
                        ).values('exam_teacher_subject__teacher_subject__subject_id')[:1]
                    ), output_field=UUIDField()
                )
                subject_name_annotation = Case(
                    When(
                        condition=Q(student_application__application__exam__is_abstract=True), 
                        then=F('question__subject__name')
                    ),
                    default=Subquery(
                        ExamQuestion.objects.using('readonly2').filter(
                            question=OuterRef('question'),
                            exam=OuterRef('student_application__application__exam')
                        ).values('exam_teacher_subject__teacher_subject__subject__name')[:1]
                    )
                )
            
            if type != 'sum':
                annotations['grade_annotation'] = grade_annotation

            annotations['answer_id'] = F('id')
            annotations['classe_id'] = Subquery(
                SchoolClass.objects.using('readonly2').filter(
                    students=OuterRef('student_application__student_id'),
                    temporary_class=False,
                ).distinct().order_by(
                    '-school_year'
                ).values('id')[:1]
            )
            annotations['application_student'] = F('student_application')
            annotations['_question'] = question_annotation
            annotations['subject_id'] = subject_id_annotation
            annotations['subject_name'] = subject_name_annotation
            annotations['question_category'] = question_category_annotation
            annotations['student'] = F('student_application__student')
            annotations['answered'] = answered_annotation
            annotations['question_weight'] = question_weight_annotation
            annotations['hit'] = hit_annotation
            annotations['application_date'] = F('student_application__application__date')
            annotations['exam'] = F('student_application__application__exam')

            return annotations

        query_file_answers = FileAnswer.objects.using('readonly2').filter(
            Q(
                student_application__student__client=self.client,
                created_at__date__year__gte=self.year,
            ),
        ).annotate(
            **common_annotations(type='discursive'),
        ).values(
            'answer_id',
            'application_student',
            '_question',
            'subject_id',
            'subject_name',
            'question_category',
            'hit',
            'student', 
            'classe_id',
            'grade_annotation', 
            'question_weight', 
            'application_date', 
            'exam', 
            'answered',
        ).distinct().query

        query_textual_answers = TextualAnswer.objects.using('readonly2').filter(
            Q(
                student_application__student__client=self.client,
                created_at__date__year__gte=self.year,
            ),
        ).annotate(
            **common_annotations(type='discursive'),
        ).values(
            'answer_id',
            'application_student',
            '_question',
            'subject_id',
            'subject_name',
            'question_category',
            'hit',
            'student', 
            'classe_id',
            'grade_annotation', 
            'question_weight', 
            'application_date', 
            'exam', 
            'answered',
        ).distinct().query

        query_option_answers = OptionAnswer.objects.using('readonly2').filter(
            student_application__student__client=self.client,
            created_at__date__year__gte=self.year,
            status=OptionAnswer.ACTIVE,
        ).annotate(
            **common_annotations(type='choice')
        ).values(
            'answer_id',
            'application_student',
            '_question',
            'subject_id',
            'subject_name',
            'question_category',
            'hit',
            'student', 
            'classe_id',
            'grade_annotation', 
            'question_weight', 
            'application_date', 
            'exam', 
            'answered',
        ).distinct().query

        query_sum_answers = SumAnswer.objects.using('readonly2').filter(
            student_application__student__client=self.client,
            created_at__date__year__gte=self.year,
        ).annotate(
            **common_annotations(type='sum'),
        ).annotate(
            grade_annotation=F('grade'),
        ).values(
            'answer_id',
            'application_student',
            '_question',
            'subject_id',
            'subject_name',
            'question_category',
            'hit',
            'student', 
            'classe_id',
            'grade_annotation', 
            'question_weight', 
            'application_date', 
            'exam', 
            'answered',
        ).distinct().query

        df_file_answers = pl.read_database_uri(query=get_query(query_file_answers), uri=self.uri).select(
            'answer_id',
            'application_student',
            '_question',
            'subject_id',
            'subject_name',
            'question_category',
            'hit',
            'student', 
            'classe_id',
            'grade_annotation', 
            'question_weight', 
            'application_date', 
            'exam', 
            'answered',
        )
        df_textual_answer = pl.read_database_uri(query=get_query(query_textual_answers), uri=self.uri).select(
            'answer_id',
            'application_student',
            '_question',
            'subject_id',
            'subject_name',
            'question_category',
            'hit',
            'student', 
            'classe_id',
            'grade_annotation', 
            'question_weight', 
            'application_date', 
            'exam', 
            'answered',
        )
        df_option_answers = pl.read_database_uri(query=get_query(query_option_answers), uri=self.uri).select(
            'answer_id',
            'application_student',
            '_question',
            'subject_id',
            'subject_name',
            'question_category',
            'hit',
            'student', 
            'classe_id',
            'grade_annotation', 
            'question_weight', 
            'application_date', 
            'exam', 
            'answered',
        )
        df_sum_answers = pl.read_database_uri(query=get_query(query_sum_answers), uri=self.uri).with_columns(
            pl.col('grade_annotation').fill_nan(0).fill_null(0).alias('grade_annotation')
        ).select(
            'answer_id',
            'application_student',
            '_question',
            'subject_id',
            'subject_name',
            'question_category',
            'hit',
            'student', 
            'classe_id',
            'grade_annotation', 
            'question_weight', 
            'application_date', 
            'exam', 
            'answered',
        )
        
        df = (
            df_file_answers
            .vstack(df_textual_answer)
            .vstack(df_option_answers)
            .vstack(df_sum_answers)
        ).rename({
            'student': 'student_id',
            'exam': 'exam_id',
            'application_student': 'application_student_id',
            'grade_annotation': 'grade',
        })
        
        # Deixa apenas as respostas que estão em alguma questão available
        df_questions_availables = (
            pl.read_parquet(f'{self.save_path}/exam_questions.parquet')
            .rename({ 'question_id': '_question' })
            .filter(pl.col('is_available'))
            .select('_question', 'question_category', 'subject_id')
        )
        
        df = df.join(df_questions_availables, on='_question', how='semi')
        
        # Faz anotações com o proprio polars
        df = df.with_columns(
            (pl.col('grade') / pl.col('question_weight') * 100).round(0).alias('performance'),
            ((pl.col('grade') > 0) & (pl.col('grade') < pl.col('question_weight'))).alias('partial_hit'),
        ).rename(
            {
                '_question': 'question_id',
            }
        ).select(
            'answer_id',
            'application_student_id', 
            'question_id', 
            'student_id', 
            'grade', 
            'classe_id', 
            'answered',
            'question_weight', 
            'partial_hit', 
            'hit', 
            'subject_id', 
            'subject_name',
            'application_date', 
            'exam_id', 
            'question_category', 
            'performance',
        ).unique(subset=['application_student_id', 'question_id', 'exam_id'])
        
        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo

        print(f"{'-' * 20} Terminou {filename} em {time.time() - self.start_time} {'-' * 20}")
        print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")

    def create_fake_answers_data(self, filename):
        
        df_applications = (
            pl.scan_parquet(f'{self.save_path}/applications.parquet')
            .unique('application_id')
            .filter(pl.col('applied') == True)
            .select('exam_id')
        )
        
        df_exams = pl.scan_parquet(f'{self.save_path}/exams.parquet').select('exam_id', 'is_foreign_language').unique()
        
        df_applied_exams = df_exams.join(df_applications, on='exam_id', how='semi')
        
        df_exam_questions = (
            pl.scan_parquet(f'{self.save_path}/exam_questions.parquet')
            .join(df_applied_exams, on='exam_id', how='semi')
            .unique(subset=['id'])
            .filter(
                pl.col('is_available'),
            )
            .sort(by=['exam_teacher_subject_order', 'order'])
            .with_columns(
                pl.int_range(0, pl.len()).over("exam_id").alias("fake_index") + 1
            )
            .select('exam_id', 'question_id', 'question_category', 'weight', 'subject_id', 'fake_index')
            .rename({ 'weight': 'question_weight' })
        )
        
        df_exam_questions = df_exam_questions.join(df_exams, on='exam_id', how='inner')
                    
        df_subjects = (
            pl.scan_parquet(f'{self.save_path}/subjects.parquet')
            .select('subject_id', 'subject_name')
        )
        
        df_exam_questions = (
            df_exam_questions.join(df_subjects, on='subject_id', how='inner')
        )
        
        df_applications_student = (
            pl.scan_parquet(f'{self.save_path}/applications_student.parquet')
            .unique(subset=['application_student_id'])
            .filter(pl.col('is_present') == True)
            .select('application_student_id', 'exam_id', 'application_date', 'student_id', 'classe_id', 'foreign_language')
        )
        
        df_applications_student = (
            df_applications_student
            .join(df_applied_exams, on='exam_id', how='semi')
        )
        
        # Junta as applications students com as questões availables
        # Vou ter [application_student, exam_id, question_id, question_category]
        df = (
            df_applications_student.join(df_exam_questions, on='exam_id', how='inner')
        )
        
        # Pega todas as respostas
        df_answers = (
            pl.scan_parquet(f'{self.save_path}/real_answers.parquet')
            .select('application_student_id', 'exam_id', 'question_id', 'question_category', 'student_id')
            .unique(subset=['application_student_id', 'exam_id', 'question_id'])
        )

        df = (
            df
            .join(df_answers, on=['application_student_id', 'exam_id', 'question_id'], how='anti')
            .filter(
                ~(
                    (pl.col("is_foreign_language") == True) & (
                        ((pl.col("foreign_language") == 1) & (pl.col("fake_index").is_between(1, 5))) |  # Remove as 5 primeiras para inglês
                        ((pl.col("foreign_language") == 0) & (pl.col("fake_index").is_between(6, 10)))  # Remove 6-10 para espanhol
                    )
                )
            )
            .with_columns(
                pl.lit(None).alias('answer_id'),
                pl.lit(0.0).alias('grade'),
                pl.lit(False).alias('answered'),
                pl.lit(False).alias('hit'),
                pl.lit(0.0).alias('performance'),
                pl.lit(False).alias('partial_hit'),
            )
            .select(
                'answer_id', 
                'application_student_id', 
                'question_id', 
                'student_id', 
                'grade', 
                'classe_id', 
                'answered', 
                'question_weight', 
                'partial_hit',
                'hit', 
                'subject_id', 
                'subject_name', 
                'application_date', 
                'exam_id', 
                'question_category', 
                'performance',
            )
            .collect()
        )
        
        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo
        
        print(f"{'-' * 20} Terminou {filename} em {time.time() - self.start_time} {'-' * 20}")
        print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")
    
    def answers_union(self, filename):
        df = pl.read_parquet(f'{self.save_path}/real_answers.parquet')
        df_fake_answers = pl.read_parquet(f'{self.save_path}/fake_answers.parquet')
        
        df = df.vstack(df_fake_answers)
        
        df.write_parquet(f'{self.save_path}/{filename}.parquet')
        
    def create_applications_student_data(self, filename):
        query_applications_student = ApplicationStudent.objects.using('readonly2').filter(
            student__client=self.client,
            created_at__year__gte=self.year,
        ).annotate(
            application_date=F('application__date'),
            application_category=F('application__category'),
            exam_id=F('application__exam__id'),
            objective_pages_sent_count=Coalesce(
                Subquery(
                    OMRStudents.objects.using('readonly2').filter(
                        application_student=OuterRef('pk'),
                        scan_image__isnull=False,
                    ).values('application_student').annotate(Count('pk')).values('pk__count')[:1]
                ),
                0
            ),
            discursive_pages_sent_count=Coalesce(
                Subquery(
                    OMRDiscursiveScan.objects.using('readonly2').filter(
                        omr_student__application_student=OuterRef('pk'),
                        upload_image__isnull=False,
                    ).values('omr_student').annotate(Count('pk')).values('pk__count')[:1]
                ),
                0
            )
        ).values(
            'id',
            'exam_id',
            'student_id',
            'application',
            'application_category',
            'application_date',
            'missed',
            'objective_pages_sent_count',
            'discursive_pages_sent_count',
            'foreign_language',
        ).distinct().query
        
        df = pl.read_database_uri(query=get_query(query_applications_student), uri=self.uri)
        
        df = df.rename({
            'id': 'application_student_id',
        }).with_columns(
            pl
            .when(pl.col('missed') == True)
            .then(False)
            .otherwise(True)
            .alias('is_present')
        ).with_columns(
            pl.col('foreign_language').fill_null(0).alias('foreign_language')
        ).select(
            'application_student_id', 
            'student_id', 
            'exam_id',
            'is_present', 
            'application_id',
            'application_category',
            'application_date',
            'missed',
            'objective_pages_sent_count',
            'discursive_pages_sent_count',
            'foreign_language',
        )

        df = df.join(pl.read_parquet(f'{self.save_path}/students.parquet').select('student_id', 'student_name', 'classe_id', 'classe_name'), on='student_id', how='inner')
        df = df.join(pl.read_parquet(f'{self.save_path}/exams.parquet').unique(subset=['exam_id', 'unity_id']).select('exam_id', 'exam_name', 'unity_id', 'unity_name'), on='exam_id', how='inner')
        df = df.join(pl.read_parquet(f'{self.save_path}/applications.parquet').unique('application_id').select('application_id', 'applied'), on='application_id', how='inner')
        
        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo
        
        print(f"{'-' * 20} Terminou {filename} em {time.time() - self.start_time} {'-' * 20}")
        print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")

    def create_applications_data(self, filename):
        query_applications = (
            Application.objects.using('readonly2').filter(
                exam__coordinations__unity__client=self.client,
                date__year__gte=self.year,
                automatic_creation=False
            ).annotate(
                finish_datetime=Case(
                    When(
                        Q(category=Application.HOMEWORK), then=F('date_end') + F('end')
                    ),
                    default=F('date') + F('end'), 
                    output_field=DateTimeField()
                ),
                applied=Case(
                    When(
                        Q(finish_datetime__lt=timezone.localtime(timezone.now())), then=Value(True)
                    ),
                    default=Value(False), 
                ),
            ).values(
                'id',
                'date',
                'exam',
                'category',
                'deadline_for_correction_of_responses',
                'deadline_for_sending_response_letters',
                'applied',
            )
            .distinct().query
        )

        df = pl.read_database_uri(query=get_query(query_applications), uri=self.uri)

        df = df.with_columns(
            pl.col("id").alias('application_id'),
            pl.col("date").alias('application_date'),
            pl.col("category").alias('application_category'),
        ).select(
            'application_id', 
            'application_date', 
            'application_category',
            'exam_id', 
            'deadline_for_correction_of_responses', 
            'deadline_for_sending_response_letters',
            'applied',
        )
        
        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo

        print(f"{'-' * 20} Terminou {filename} em {time.time() - self.start_time} {'-' * 20}")
        print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")

    
    def create_teachers_data(self, filename):
        query_inspectors = (
            Inspector.objects.using('readonly2')
            .filter(
                coordinations__unity__client=self.client,
                is_abstract=False,
            )
            .annotate(
                first_subject_name=Subquery(
                    TeacherSubject.objects.filter(
                        teacher__pk=OuterRef('pk'),
                        active=True,
                        school_year__gte=self.year,
                    ).values('subject__name')[:1]
                ),
                teacher_subject_active=Coalesce(
                    Subquery(
                        TeacherSubject.objects.filter(
                            teacher__pk=OuterRef('pk'),
                            active=True,
                            school_year__gte=self.year,
                        ).order_by('created_at').values('active')[:1], 
                    ),
                    Value(False),
                    output_field=BooleanField()
                )
            )
            .values(
                'id',
                'name',
                'coordinations__unity',
                'is_discipline_coordinator',
                'user__is_active',
                'first_subject_name',
                'teacher_subject_active',
            )
            .distinct().query
        )
        
        try:

            df = pl.read_database_uri(query=get_query(query_inspectors), uri=self.uri)
            df = df.rename({ 
                'id': 'teacher_id',
                'name': 'teacher_name',
                'first_subject_name': 'subject_name',
            }).select(
                'teacher_id', 
                'teacher_name',
                'unity_id',
                'is_discipline_coordinator',
                'is_active',
                'subject_name',
                'teacher_subject_active',
            )
            
            df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo

            print(f"{'-' * 20} Terminou {filename} em {time.time() - self.start_time} {'-' * 20}")
            print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")

        except Exception as e:
            print("Erro em create_teachers_data:", e)

    def create_students_data(self, filename):

        query_students = Student.objects.using('readonly2').filter(
            client=self.client,
            classes__temporary_class=False,
        ).annotate(
            student_name=F('name'),
            classe_id=Subquery(
                SchoolClass.objects.using('readonly2').filter(
                    students=OuterRef('pk'),
                    temporary_class=False,
                ).distinct().order_by(
                    '-school_year'
                ).values('id')[:1]
            ),
            classe_name=Subquery(
                SchoolClass.objects.using('readonly2').filter(
                    students=OuterRef('pk'),
                    temporary_class=False,
                ).distinct().order_by(
                    '-school_year'
                ).values('name')[:1]
            ),
            unity_id=Subquery(
                SchoolClass.objects.using('readonly2').filter(
                    students=OuterRef('pk'),
                    temporary_class=False,
                ).distinct().order_by(
                    '-school_year'
                ).values('coordination__unity__id')[:1]
            ),
        ).values(
            'id',
            'student_name',
            'classe_id',
            'classe_name',
            'unity_id',
        ).distinct().query
        
        df = pl.read_database_uri(query=get_query(query_students), uri=self.uri)

        df = df.rename({
            'id': 'student_id'
        }).select(
            'student_id', 
            'student_name', 
            'classe_id', 
            'classe_name', 
            'unity_id',
        )
        
        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo
        
        print(f"{'-' * 20} Terminou {filename} em {time.time() - self.start_time} {'-' * 20}")
        print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")

    def create_bnccs_data(self, filename):
        
        query_available_questions_topics = ExamQuestion.objects.using('readonly2').filter(
            updated_at__date__year__gte=self.year,
        ).availables_without_distinct(
            exclude_annuleds=True
        ).filter(
            question__topics__isnull=False
        ).annotate(
            bncc_code=Value(''),
            bncc_type=Value('topic'),
        ).values(
            'question',
            'question__topics',
            'question__topics__name',
            'bncc_code',
            'bncc_type',
        ).query

        query_available_questions_competences = ExamQuestion.objects.using('readonly2').filter(
            updated_at__date__year__gte=self.year,
        ).availables_without_distinct(
            exclude_annuleds=True
        ).filter(
            question__competences__isnull=False
        ).annotate(
            bncc_type=Value('competence'),
        ).values(
            'question',
            'question__competences',
            'question__competences__text',
            'question__competences__code',
            'bncc_type',
        ).query

        query_available_questions_abilities = ExamQuestion.objects.using('readonly2').filter(
            updated_at__date__year__gte=self.year,
        ).availables_without_distinct(
            exclude_annuleds=True
        ).filter(
            question__abilities__isnull=False
        ).annotate(
            bncc_type=Value('abillity'),
        ).values(
            'question',
            'question__abilities',
            'question__abilities__text',
            'question__abilities__code',
            'bncc_type',
        ).query
        
        try:

            df_topics = pl.read_database_uri(query=get_query(query_available_questions_topics), uri=self.uri).with_columns(
                pl.col('question_id'),
                pl.col('topic_id').alias('bncc_id'),
                pl.col('name').alias('bncc_text'),
            ).select('question_id', 'bncc_id', 'bncc_type', 'bncc_text', 'bncc_code')
            df_competences = pl.read_database_uri(query=get_query(query_available_questions_competences), uri=self.uri).with_columns(
                pl.col('question_id'),
                pl.col('competence_id').alias('bncc_id'),
                pl.col('code').alias('bncc_code'),
                pl.col('text').alias('bncc_text'),
            ).select('question_id', 'bncc_id', 'bncc_type', 'bncc_text', 'bncc_code')
            df_abilities = pl.read_database_uri(query=get_query(query_available_questions_abilities), uri=self.uri).with_columns(
                pl.col('question_id'),
                pl.col('abiliity_id').alias('bncc_id'),
                pl.col('code').alias('bncc_code'),
                pl.col('text').alias('bncc_text'),
            ).select('question_id', 'bncc_id', 'bncc_type', 'bncc_text', 'bncc_code')

            df = df_topics.vstack(df_competences)
            df = df.vstack(df_abilities)
            
            df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo

            print(f"{'-' * 20} Terminou {filename} em {time.time() - self.start_time} {'-' * 20}")
            print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")

        except Exception as e:
            print("An error occurred:", e)