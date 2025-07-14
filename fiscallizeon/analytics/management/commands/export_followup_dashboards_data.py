from django.core.management.base import BaseCommand
import polars as pl
import os, time, math
from decouple import config
from fiscallizeon.answers.models import FileAnswer, TextualAnswer, OptionAnswer, SumAnswer
from fiscallizeon.exams.models import ExamQuestion, Exam, ExamTeacherSubject, StatusQuestion, TeacherSubject
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.students.models import Student
from fiscallizeon.subjects.models import Subject
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.omr.models import OMRStudents, OMRDiscursiveScan

from django.db.models import F, When, Case, DateTimeField, Value, Q, Subquery, OuterRef, Sum, Count, Exists
from django.db.models.functions import Coalesce, Concat
from django.db import connection
from django.utils import timezone
from fiscallizeon.classes.models import SchoolClass
from datetime import timedelta
from fiscallizeon.clients.models import Client, Unity
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
    days_after = timezone.now() - timedelta(days=15)

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
                print("########## >>>", client.name)
                self.client = str(client.id)
                
                self.save_path = f'tmp/dashboards/{self.client}/followup'
                os.makedirs(f'{self.save_path}', exist_ok=True)
                
                self.create_unities_data(filename='unities')
                self.create_school_classes_data(filename='school_classes')
                self.create_teachers_data(filename='teachers')
                self.create_exams_teacher_subject_data(filename='exam_teacher_subjects')
                self.create_subjects_data(filename='subjects')
                self.create_exam_questions_data(filename='exam_questions')
                self.create_students_data(filename='students')
                self.create_exams_data(filename='exams')
                self.create_applications_data(filename='applications')
                self.create_applications_student_data(filename='applications_student')
                self.create_applications_classes_data(filename='applications')
                self.create_status_question_data(filename='status_questions')
                self.create_real_answers_data(filename='real_answers')
                self.create_fake_answers_data(filename='fake_answers')
                self.create_union_data(filename='answers')
                
                # Followup
                self.create_followup_question_elaboration_data(filename='followup-questions')
                time.sleep(5)
                self.create_followup_cards_upload_data(filename='followup-uploads')
                time.sleep(5)
                self.create_followup_reviews_data(filename='followup-reviews')
                time.sleep(5)
                self.create_followup_corrections_data(filename='followup-corrections')

                client.last_generation_followup_dashboard = timezone.now()
                client.save(skip_hooks=True)
                
            except Exception as e:
                print("########## >>>", client.name) 
                print(e)

        print(f"no geral demorou: {time.time() - self.start_time}")

    def create_subjects_data(self, filename):
        
        print(f"{'*' * 20} chamou create_subjects_data {'*' * 20}")
        
        query_subjects = Subject.objects.using('readonly2').annotate(
            subject_name=Concat(
                F('name'),
                Value(' - '),
                F('knowledge_area__name'),
            ),
        ).values(
            'id',
            'subject_name',
        ).distinct().query

        df = pl.read_database_uri(query=get_query(query_subjects), uri=self.uri).rename({ 'id': 'subject_id' }).select('subject_id', 'subject_name')
        
        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo
        
        print(f"{'-' * 20} Terminou create_subjects_data em {time.time() - self.start_time} {'-' * 20}")
        print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")
    
    def create_exam_questions_data(self, filename):
        
        print(f"{'*' * 20} chamou create_exam_questions_data {'*' * 20}")
        
        exam_questions = ExamQuestion.objects.using('readonly2').filter(
            is_abstract=False,
            created_at__year=self.year
        ).distinct()

        query_exam_questions = exam_questions.annotate(
            is_available=Value(False),
            question_category=F('question__category'),
            quantity_lines=F('question__quantity_lines'),
        ).values(
            'id',
            'exam_id',
            'question',
            'question_category',
            'quantity_lines',
            'is_available',
            'weight',
        ).query

        query_exam_questions_availables = exam_questions.availables(
            exclude_annuleds=True
        ).annotate(
            is_available=Value(True),
            question_category=F('question__category'),
            quantity_lines=F('question__quantity_lines'),
        ).values(
            'id',
            'exam_id',
            'question',
            'question_category',
            'quantity_lines',
            'is_available',
            'weight',
        ).query
        
        df_exam_questions = pl.read_database_uri(query=get_query(query_exam_questions), uri=self.uri).rename({'id': 'exam_question_id'}).select(
            'exam_question_id',
            'exam_id',
            'question_id',
            'question_category',
            'quantity_lines',
            'is_available',
            'weight',
        )

        df_exam_questions_availables = pl.read_database_uri(query=get_query(query_exam_questions_availables), uri=self.uri).rename({'id': 'exam_question_id'}).select(
            'exam_question_id',
            'exam_id',
            'question_id',
            'question_category',
            'quantity_lines',
            'is_available',
            'weight',
        )

        df_all = df_exam_questions.join(df_exam_questions_availables, on=['exam_id', 'question_id'], how='anti')

        df = df_all.vstack(df_exam_questions_availables)
        
        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo
        # df.write_csv(f'{self.save_path}/{filename}.csv') # Salva em arquivo

        print(f"{'-' * 20} Terminou {filename} em {time.time() - self.start_time} {'-' * 20}")
        print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")

    def create_status_question_data(self, filename):

        print(f"{'*' * 20} chamou create_status_question_data {'*' * 20}")
        
        df_exams = (
            pl.scan_parquet(f'{self.save_path}/exams.parquet')
            .filter(pl.col('review_deadline').dt.date() >= self.days_after.date())
            .select('exam_id')
            .unique()
        )

        exam_questions_ids = (
            pl.scan_parquet(f'{self.save_path}/exam_questions.parquet')
            .join(df_exams.select('exam_id'), on='exam_id', how='semi')
            .filter(pl.col('is_available') == True)
            .select('exam_question_id')
            .unique('exam_question_id')
            .collect()
            .to_dict(as_series=False)
            .get('exam_question_id')
        )
        
        query_status_questions = StatusQuestion.objects.using('readonly2').filter(
            Q(user__isnull=False),
            Q(exam_question__in=exam_questions_ids) if exam_questions_ids else Q(pk__isnull=True),
        ).values(
            'id',
            'exam_question_id',
            'status',
            'exam_question__exam_id',
            'exam_question__exam_teacher_subject_id',
            'user_id',
        ).query
        
        df = (
            pl.read_database_uri(query=get_query(query_status_questions), uri=self.uri)
            .rename({
                'id': 'statusquestion_id',
            })
            .unique(subset=['exam_question_id', 'user_id'])
        )

        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo

        print(f"{'-' * 20} Terminou create_status_question_data em {time.time() - self.start_time} {'-' * 20}")
        print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")
    
    def create_exams_data(self, filename):
        print(f"{'*' * 20} chamou create_exams_data {'*' * 20}")
        
        query_exams = Exam.objects.using('readonly2').filter(
            created_at__date__year=self.year,
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
            'review_deadline',
            'release_elaboration_teacher',
            'total_solicitation',
            'coordinations__unity',
            'teacher_id',
            'teacher_name',
            'status',
            'category',
            'teaching_stage',
            'teaching_stage_name',
            'education_system',
            'education_system_name',
            'created_by',
        ).distinct().query

        df = (
            pl.read_database_uri(query=get_query(query_exams), uri=self.uri)
        )

        # df.write_csv(f'{self.save_path}/{filename}.csv') # Salva em arquivo
        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo

        print(f"{'-' * 20} Terminou create_exams_data em {time.time() - self.start_time} {'-' * 20}")
        print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")
    
    def create_exams_teacher_subject_data(self, filename):

        print(f"{'*' * 20} chamou create_exams_teacher_subject_data {'*' * 20}")
        
        df_unities = (
            pl.scan_parquet(f'{self.save_path}/unities.parquet')
        )
        
        df_teachers = (
            pl.scan_parquet(f'{self.save_path}/teachers.parquet')
            .join(df_unities, on='unity_id', how='left')
            .group_by('teacher_id', 'unity_id', 'unity_name')
            .agg()
            .collect()
        )
        
        teachers_ids = df_teachers.select('teacher_id').unique().get_column('teacher_id').to_list()
        
        query_exam_teacher_subjects = ExamTeacherSubject.objects.using('readonly2').filter(
            # exam__review_deadline__gte=self.days_after.date(),
            teacher_subject__teacher__in=teachers_ids,
            exam__coordinations__unity__client=self.client,
        ).annotate(
            review_deadline=F('exam__review_deadline'),
            teacher_id=F('teacher_subject__teacher_id'),
            teacher_name=F('teacher_subject__teacher__name'),
            questions_count=Subquery(
                ExamQuestion.objects.using('readonly2').filter(
                    Q(exam_teacher_subject=OuterRef('pk'))
                )
                .availables_without_distinct(exclude_annuleds=True)
                .values('exam_teacher_subject')
                .annotate(
                    total=Count('pk', distinct=True)
                ).values('total')[:1]
            ),
            reviewed_by_user=F('reviewed_by__user__id'),
        ).values(
            'id',
            'exam',
            'teacher_subject__subject',
            'teacher_id',
            'quantity',
            'questions_count',
            'reviewed_by_user',
            'review_deadline',
            'grade',
        ).query

        df = (
            pl.read_database_uri(query=get_query(query_exam_teacher_subjects), uri=self.uri)
            .rename({
                'id': 'exam_teacher_subject_id',
            })
            .select(
                'exam_teacher_subject_id', 
                'exam_id', 
                'teacher_id', 
                'subject_id',
                'quantity', 
                'questions_count',
                'reviewed_by_user',
                'review_deadline',
                'grade_id',
            )
            .unique()
        )
        
        df = (
            df
            .join(df_teachers, on='teacher_id', how='inner')
        )
        
        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo
        print(f"{'-' * 20} Terminou create_exams_teacher_subject_data em {time.time() - self.start_time} {'-' * 20}")
        print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")
    
    def create_real_answers_data(self, filename):

        print(f"{'*' * 20} Iniciou create_real_answers_data {'*' * 20}")

        def common_annotations(type='discursive'):   
            
            annotations = {}

            if type == 'discursive':
                question_annotation = F('question')
                answered_annotation=Case(
                    When(
                        condition=Q(
                            Q(
                                Q(grade__isnull=False) |
                                Q(empty=True)
                            )
                        ), then=Value(True),
                    ), default=Value(False)
                )
            elif type == 'choice':
                question_annotation = F('question_option__question')
                answered_annotation = Value(True)

            elif type == 'sum':
                question_annotation = F('question')
                answered_annotation = Value(True)

            annotations['answer_id'] = F('id')
            annotations['application_student'] = F('student_application')
            annotations['application_id'] = F('student_application__application')
            # annotations['unity_id'] = F('student_application__application__school_classes__coordination__unity')
            annotations['_question'] = question_annotation
            annotations['answered'] = answered_annotation
            annotations['exam'] = F('student_application__application__exam')

            return annotations

        df_applications = pl.read_parquet(f'{self.save_path}/applications.parquet').select('application_id').get_column('application_id').to_list()

        query_file_answers = FileAnswer.objects.using('readonly2').filter(
            Q(student_application__application__in=df_applications) if df_applications else Q(pk__isnull=True),
            Q(created_at__year=self.year),
        ).annotate(
            **common_annotations(type='discursive'),
        ).values(
            'answer_id',
            'exam', 
            'application_student',
            'application_id',
            '_question',
            # 'unity_id',
            'answered',
        ).distinct().query

        query_textual_answers = TextualAnswer.objects.using('readonly2').filter(
            Q(student_application__application__in=df_applications) if df_applications else Q(pk__isnull=True),
            Q(created_at__year=self.year),
        ).annotate(
            **common_annotations(type='discursive'),
        ).values(
            'answer_id',
            'exam', 
            'application_student',
            'application_id',
            '_question',
            # 'unity_id',
            'answered',
        ).distinct().query

        query_option_answers = OptionAnswer.objects.using('readonly2').filter(
            Q(
                Q(student_application__application__in=df_applications) if df_applications else Q(pk__isnull=True),
            ),
            Q(created_at__year=self.year),
            Q(status=OptionAnswer.ACTIVE),
        ).annotate(
            **common_annotations(type='choice')
        ).values(
            'answer_id',
            'exam', 
            'application_student',
            'application_id',
            '_question',
            # 'unity_id',
            'answered',
        ).distinct().query

        query_sum_answers = SumAnswer.objects.using('readonly2').filter(
            Q(student_application__application__in=df_applications) if df_applications else Q(pk__isnull=True),
            Q(created_at__year=self.year),
        ).annotate(
            **common_annotations(type='sum')
        ).values(
            'answer_id',
            'exam', 
            'application_student',
            'application_id',
            '_question',
            # 'unity_id',
            'answered',
        ).distinct().query

        df_file_answers = pl.read_database_uri(query=get_query(query_file_answers), uri=self.uri)
        df_textual_answer = pl.read_database_uri(query=get_query(query_textual_answers), uri=self.uri)
        df_sum_answers = pl.read_database_uri(query=get_query(query_sum_answers), uri=self.uri)
        df_option_answers = pl.read_database_uri(query=get_query(query_option_answers), uri=self.uri)
        
        df = (
            df_option_answers
            .vstack(df_textual_answer)
            .vstack(df_file_answers)
            .vstack(df_sum_answers)
        )

        # Deixa apenas as respostas que estão em alguma questão available
        df_questions_availables = (
            pl.read_parquet(f'{self.save_path}/exam_questions.parquet')
            .rename({ 'question_id': '_question' })
            .filter(pl.col('is_available'))
            .select('_question')
            .unique()
        )
        
        df = (
            df
            .join(df_questions_availables, on='_question', how='inner')
        )
        
        df_school_classes = (
            pl.read_parquet(f'{self.save_path}/school_classes.parquet')
            .select('classe_id', 'unity_id')
            .group_by('classe_id', 'unity_id')
            .agg()
        )
        
        df_applications = (
            pl.read_parquet(f'{self.save_path}/applications.parquet')
            .select('application_id', 'classe_id')
            .join(df_school_classes, on='classe_id', how='inner')
        )

        df = (
            df
            .join(df_questions_availables, on='_question', how='inner')
            .join(df_applications, on='application_id', how='inner')
        )
        
        # Faz anotações com o proprio polars
        df = (
            df
            .rename({
                'exam': 'exam_id',
                '_question': 'question_id', 
                'application_student': 'application_student_id'
            })
            .select(
                'answer_id',
                'exam_id', 
                'application_student_id',
                'question_id',
                'unity_id',
                'answered',
            )
            # .unique(subset=['application_student', 'question_id', 'exam_id'])
        )
        
        chunks_list = []
        chunk_size = 1000000
        
        for i in range(0, df.height, chunk_size):
            chunk = df.slice(i, chunk_size)
            
            chunk_unique = chunk.unique(subset=['application_student_id', 'question_id', 'exam_id'])
            chunks_list.append(chunk_unique)
                    
        if len(chunks_list) >= 2:
            
            df: pl.DataFrame = (
                pl.concat(chunks_list)
            )
                
        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo
        
        print(f"{'-' * 20} Terminou create_real_answers_data em {time.time() - self.start_time} {'-' * 20}")
        print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")

    def create_fake_answers_data(self, filename):
        import uuid
        
        print(f"{'*' * 20} Iniciou create_fake_answers_data {'*' * 20}")

        df_applications = (
            pl.scan_parquet(f'{self.save_path}/applications.parquet')
            .select('application_id', 'classe_id')
        )

        # Deixa apenas as respostas que estão em alguma questão available
        df_questions_availables = (
            pl.scan_parquet(f'{self.save_path}/exam_questions.parquet')
            .filter(pl.col('is_available'))
            .unique()
        )
        
        df_applications_student = (
            pl.scan_parquet(f'{self.save_path}/applications_student.parquet')
            .filter(
                pl.col('empty_question_id').is_not_null()
            )
            .rename({
                'empty_question_id': 'question_id',
            })
            .join(df_applications.select('application_id').unique(), on='application_id', how='semi')
            .join(df_questions_availables, on='question_id', how='semi')
        )
        
        df_school_classes = (
            pl.scan_parquet(f'{self.save_path}/school_classes.parquet')
            .select('classe_id', 'unity_id')
            .group_by('classe_id', 'unity_id')
            .agg()
        )
        

        df = (
            df_applications_student
            .join(df_applications, on='application_id', how='inner')
            .join(df_school_classes, on='classe_id', how='inner')
            .collect()
        )
        
        uuids = [str(uuid.uuid4()) for _ in range(df.height)]
        
        df = (
            df
            .with_columns(
                pl.Series(uuids).alias("answer_id"),
                pl.lit(True).alias('answered'),
            )
            .select(
                'answer_id',
                'exam_id', 
                'application_student_id',
                'question_id',
                'unity_id',
                'answered',
            )
            .unique()
        )
        
        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo
        # df.write_csv(f'{self.save_path}/{filename}.csv') # Salva em arquivo
        
        print(f"{'-' * 20} Terminou create_fake_answers_data em {time.time() - self.start_time} {'-' * 20}")
        print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")

    def create_union_data(self, filename):

        df_real_answers = (
            pl.read_parquet(f'{self.save_path}/real_answers.parquet')
        )
        df_fake_answers = (
            pl.read_parquet(f'{self.save_path}/fake_answers.parquet')
        )
        
        df = pl.concat([df_real_answers, df_fake_answers])
        
        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo
        
        print(f"{'-' * 20} Terminou create_union_data em {time.time() - self.start_time} {'-' * 20}")
        print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")
    
    def create_applications_student_data(self, filename):
        
        print(f"{'*' * 20} Iniciou create_applications_student_data {'*' * 20}")
        
        applications_ids = pl.scan_parquet(f'{self.save_path}/applications.parquet').select('application_id').unique().collect().to_dict(as_series=False).get('application_id')
        
        query_applications_student = ApplicationStudent.objects.using('readonly2').filter(
            Q(application__in=applications_ids) if applications_ids else Q(pk__isnull=True)
        ).annotate(
            application_date=F('application__date'),
            exam_id=F('application__exam__id'),
            exam_name=F('application__exam__name'),
            student_name=F('student__name'),
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
            ),
            has_school_classes=Exists(
                SchoolClass.objects.using('readonly2').filter(
                    applications=OuterRef('application__pk'),
                    temporary_class=False,
                    school_year=self.year,
                )
            ),
            classe_id=Case(
                When(
                    Q(has_school_classes=False),
                    then=Subquery(
                        SchoolClass.objects.using('readonly2').filter(
                            students=OuterRef('student__pk'),
                            temporary_class=False,
                            school_year=self.year,
                        ).order_by('created_at').distinct().values('id')[:1]
                    )
                ),
                default=Subquery(
                    SchoolClass.objects.using('readonly2').filter(
                        applications=OuterRef('application__pk'),
                        students=OuterRef('student__pk'),
                        temporary_class=False,
                        school_year=self.year,
                    ).order_by('created_at').distinct().values('id')[:1]
                )
            ),
            empty_question_id=F('empty_option_questions'),
        ).values(
            'id',
            'exam_id',
            'exam_name',
            'student',
            'student_name',
            'classe_id',
            'application',
            'application_date',
            'missed',
            'objective_pages_sent_count',
            'discursive_pages_sent_count',
            'empty_question_id',
        ).distinct().query

        df = pl.read_database_uri(query=get_query(query_applications_student), uri=self.uri)
        
        df_school_classes = (
            pl.read_parquet(f'{self.save_path}/school_classes.parquet')
            .select('classe_id', 'unity_id')
            .group_by(
                'classe_id',
                'unity_id',
            )
            .agg()
        )
        
        df = df.rename({
            'id': 'application_student_id',
        }).with_columns(
            pl
            .when(pl.col('missed'))
            .then(False)
            .otherwise(True)
            .alias('is_present')
        ).join(
            df_school_classes,
            on='classe_id',
            how='inner',
        ).select(
            'application_student_id', 
            'student_id', 
            'student_name',
            'classe_id',
            'unity_id',
            'exam_id',
            'exam_name',
            'is_present', 
            'application_id',
            'application_date',
            'missed',
            'objective_pages_sent_count',
            'discursive_pages_sent_count',
            'empty_question_id',
        )
        
        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo
        
        print(f"{'-' * 20} Terminou create_applications_student_data em {time.time() - self.start_time} {'-' * 20}")
        print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")

    def get_removed_not_started_applications_student_data(self) -> pl.LazyFrame:
        
        print(f"{'*' * 20} Iniciou get_removed_not_started_applications_student_data {'*' * 20}")
        
        df_applications = (
            pl.scan_parquet(f'{self.save_path}/applications.parquet')
            .filter(
                pl.col('show_result_only_for_started_application'),
            )
            .select('application_id')
            .unique()
        )
        
        df_applications_student = (
            pl.scan_parquet(f'{self.save_path}/applications_student.parquet')
            .select('application_id', 'application_student_id')
            .join(df_applications, on='application_id', how='semi')
            .unique()
        )
        
        df_applications_student_without_answers = (
            df_applications_student
            .join(
                pl.scan_parquet(f'{self.save_path}/answers.parquet').select('application_student_id'),
                on='application_student_id',
                how='anti'
            )
        )
        
        df_answereds_applications_student = (
            pl.scan_parquet(f'{self.save_path}/applications_student.parquet')
            .join(
                df_applications_student_without_answers,
                on="application_student_id",
                how="anti"
            )
            .unique()
        )
        
        return df_answereds_applications_student
        
    def create_applications_data(self, filename):
        print(f"{'*' * 20} Iniciou create_applications_data {'*' * 20}")
        query_applications = (
            Application.objects.using('readonly2').filter(
                category=Application.PRESENTIAL,
                exam__coordinations__unity__client=self.client,
                # school_classes__isnull=False,
                automatic_creation=False,
            )
            .filter(
                Q(
                    deadline_for_correction_of_responses__gte=self.days_after.date(),
                ) |
                Q(
                    deadline_for_sending_response_letters__gte=self.days_after.date(),
                )
            )
            .annotate(
                exam_name=F('exam__name'),
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
            )
            .values(
                'id',
                'date',
                'exam',
                'exam_name',
                'category',
                'deadline_for_correction_of_responses',
                'deadline_for_sending_response_letters',
                'school_classes',
                'applied',
                'show_result_only_for_started_application',
            )
            .distinct()
            .query
        )

        df = pl.read_database_uri(query=get_query(query_applications), uri=self.uri)

        df = df.with_columns(
            pl.col("id").alias('application_id'),
            pl.col("date").alias('application_date'),
            pl.col("category").alias('application_category'),
        ).rename({
            'schoolclass_id': 'classe_id'
        }).select(
            'application_id', 
            'application_date', 
            'exam_id',
            'exam_name',
            'application_category', 
            'deadline_for_correction_of_responses', 
            'deadline_for_sending_response_letters',
            'classe_id',
            'applied',
            'show_result_only_for_started_application',
        )
        
        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo
        
        print(f"{'-' * 20} Terminou create_applications_data em {time.time() - self.start_time} {'-' * 20}")
        print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")
    
    def create_applications_classes_data(self, filename):
        """

        """
        print(f"{'*' * 20} Iniciou create_applications_classes_data {'*' * 20}")
        
        df_applications_with_classes = (
            pl.read_parquet(f'{self.save_path}/applications.parquet')
            .filter(
                pl.col('classe_id').is_not_null(),
            )
            .unique()
        )
        
        df_applications_without_classes = (
            pl.read_parquet(f'{self.save_path}/applications.parquet')
            .filter(
                pl.col('classe_id').is_null(),
            ).unique()
            .select(
                'application_id', 
                'application_date', 
                'exam_id',
                'exam_name',
                'application_category', 
                'deadline_for_correction_of_responses', 
                'deadline_for_sending_response_letters',
                'applied',
                'show_result_only_for_started_application',
            )
        )
        
        df_group_applications_student = (
            pl.read_parquet(f'{self.save_path}/applications_student.parquet')
            .filter(
                pl.col('classe_id').is_not_null(),
            )
            .group_by('application_id', 'classe_id')
            .agg()
            .unique()
        )
        
        df_applications_with_applications_student_classes = (
            df_applications_without_classes
            .join(
                df_group_applications_student, on='application_id', how='left'
            )
            .filter(
                pl.col('classe_id').is_not_null(),
            )
        )
        
        df = pl.concat([
            df_applications_with_classes.select(
                'application_id', 
                'application_date', 
                'exam_id',
                'exam_name',
                'application_category', 
                'deadline_for_correction_of_responses', 
                'deadline_for_sending_response_letters',
                'classe_id',
                'applied',
                'show_result_only_for_started_application',
            ), 
            df_applications_with_applications_student_classes.select(
                'application_id', 
                'application_date', 
                'exam_id',
                'exam_name',
                'application_category', 
                'deadline_for_correction_of_responses', 
                'deadline_for_sending_response_letters',
                'classe_id',
                'applied',
                'show_result_only_for_started_application',
            )
        ])
        
        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo
        
        print(f"{'-' * 20} Terminou create_applications_classes_data em {time.time() - self.start_time} {'-' * 20}")
        print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")
    
    def create_school_classes_data(self, filename):
        print(f"{'*' * 20} Iniciou create_school_classes_data {'*' * 20}")
        
        query_school_classes = (
            SchoolClass.objects.using('readonly2').filter(
                coordination__unity__client=self.client,
                school_year=self.year,
            )
            .annotate(
                unity_id=F('coordination__unity'),
            )
            .values(
                'id',
                'name',
                'school_year',
                'temporary_class',
                'unity_id',
                'grade',
            )
            .distinct()
            .query
        )

        df = pl.read_database_uri(query=get_query(query_school_classes), uri=self.uri)

        df = df.rename({
            'id': 'classe_id',
            'name': 'classe_name',
        }).select(
            'classe_id', 
            'classe_name', 
            'school_year',
            'temporary_class',
            'unity_id',
            'grade_id',
        )
        
        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo
        
        print(f"{'-' * 20} Terminou create_school_classes_data em {time.time() - self.start_time} {'-' * 20}")
        print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")
    
    def create_unities_data(self, filename):

        print(f"{'*' * 20} Iniciou create_unities_data {'*' * 20}")
        
        query_unities = Unity.objects.using('readonly2').filter(
            coordinations__unity__client=self.client,
        ).values(
            'id',
            'name',
        ).query
        
        df = (
            pl.read_database_uri(query=get_query(query_unities), uri=self.uri)
            .rename({
                'id': 'unity_id',
                'name': 'unity_name',
            })
            .unique()
        )
        
        # df.write_csv(f'{self.save_path}/{filename}.csv') # Utilizado apenas para teste
        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo
        print(f"{'-' * 20} Terminou create_unities_data em {time.time() - self.start_time} {'-' * 20}")
    
    def create_teachers_data(self, filename):

        print(f"{'*' * 20} Iniciou create_teachers_data {'*' * 20}")
        
        query_inspectors = Inspector.objects.using('readonly2').filter(
            Q(
                coordinations__unity__client=self.client,
                is_abstract=False,
            ),
            Q(
                Q(teachersubject__classes__school_year=self.year) |
                Q(teachersubject__classes__isnull=True)
            )
        ).annotate(
            teacher_name=F('name'),
            # unity_id=F('coordinations__unity'),
        ).values(
            'id',
            'teacher_name',
            'email',
            'user',
            'user__is_active',
            # 'unity_id',
            'is_discipline_coordinator',
            'teachersubject__subject',
            'teachersubject__classes',
        ).distinct().query

        df = pl.read_database_uri(query=get_query(query_inspectors), uri=self.uri)

        df_school_classes = (
            pl.read_parquet(f'{self.save_path}/school_classes.parquet')
            .filter(pl.col('school_year') == self.year)
            .group_by('classe_id', 'unity_id')
            .agg()
            .unique()
        )

        df = (
            df.rename({ 
                'id': 'teacher_id',
                'schoolclass_id': 'classe_id',
            }).join(
                df_school_classes,
                on='classe_id',
                how='left',    
            ).select(
                'teacher_id', 
                'teacher_name',
                'email',
                'user_id',
                'is_active',
                'unity_id',
                'is_discipline_coordinator',
                'classe_id',
                'subject_id',
            )
            .with_columns(
                (pl.col('classe_id').is_not_null()).alias('has_class_row')
            )
            .group_by([
                'teacher_id', 
                'teacher_name',
                'user_id',
                'is_active',
                'unity_id',
                'is_discipline_coordinator',
                'classe_id',
                'subject_id',
            ])
            .agg(
                pl.col('has_class_row').any().alias('has_classes')
            )
            .unique()
        )

        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo
        print(f"até aqui demorou: {time.time() - self.start_time} para salvar em parquet com as seguintes colunas: {df.columns}")

    def create_students_data(self, filename):

        print(f"{'*' * 20} Iniciou create_students_data {'*' * 20}")

        query_students = Student.objects.using('readonly2').filter(
            client=self.client,
            classes__temporary_class=False,
            classes__school_year=self.year
        ).annotate(
            student_name=F('name'),
            classe_id=Subquery(
                SchoolClass.objects.using('readonly2').filter(
                    students=OuterRef('pk'),
                    temporary_class=False,
                    school_year=self.year,
                ).distinct().order_by(
                    'created_at'
                ).values('id')[:1]
            ),
        ).values(
            'id',
            'student_name',
            'classe_id',
            'classes__coordination__unity__id',
        ).distinct().query
        

        df = pl.read_database_uri(query=get_query(query_students), uri=self.uri)

        df = df.with_columns(
            pl.col("id").alias('student_id'),
        ).select(
            'student_id', 
            'student_name', 
            'classe_id', 
            'unity_id',
        )
        
        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo

        print(f"{'-' * 20} Terminou create_students_data em {time.time() - self.start_time} {'-' * 20}")
        print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")

    def create_followup_question_elaboration_data(self, filename):
        
        print(f"{'*' * 20} Iniciou create_followup_question_elaboration_data {'*' * 20}")

        query_exam_teacher_subjects = ExamTeacherSubject.objects.using('readonly2').filter(
            exam__elaboration_deadline__gte=self.days_after.date(),
            exam__coordinations__unity__client=self.client,
            teacher_subject__teacher__user__is_active=True,
        ).annotate(
            questions_count=Subquery(
                ExamQuestion.objects.using('readonly2').filter(
                    Q(exam_teacher_subject=OuterRef('pk')),
                )
                .availables_without_distinct(exclude_annuleds=True)
                .values('exam_teacher_subject')
                .annotate(
                    total=Count('pk', distinct=True)
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
            'teacher_name',
            'exam__elaboration_deadline',
            'exam__teaching_stage',
            'teaching_stage_name',
            'exam__education_system',
            'education_system_name',
            'soliciteds',
            'questions_count',
        ).query

        df = (
            pl.read_database_uri(query=get_query(query_exam_teacher_subjects), uri=self.uri)
            .rename({
                'id': 'exam_teacher_subject_id',
                'elaboration_deadline': 'deadline',
            })
            .with_columns(
                pl.col('questions_count').fill_null(0).fill_nan(0)
            )
            .with_columns(
                pl.when(pl.col('questions_count') > pl.col('soliciteds'))
                .then(pl.col('soliciteds'))
                .otherwise(pl.col('questions_count'))
                .alias('questions_count')
            )
            .select(
                'exam_teacher_subject_id', 
                'exam_id', 
                'exam_name', 
                'soliciteds', 
                'questions_count', 
                'teacher_id', 
                'teacher_name', 
                'deadline', 
                'teaching_stage_id', 
                'teaching_stage_name', 
                'education_system_id',
                'education_system_name',
            )
            .unique()
        )
        
        df_unities = (
            pl.read_parquet(f'{self.save_path}/unities.parquet')
            .group_by('unity_id', 'unity_name')
            .agg()
            .unique()
        )
        
        df_teachers = (
            pl.read_parquet(f'{self.save_path}/teachers.parquet')
            .join(
                df_unities, on='unity_id', how='inner'
            )
            .group_by('teacher_id', 'unity_id', 'unity_name')
            .agg()
        )
        
        df = (
            df
            .join(
                df_teachers, on='teacher_id', how='inner'
            )
        )
        
    
        df.write_parquet(f'{self.save_path}/{filename}.parquet') # Salva em arquivo

        print(f"{'-' * 20} Terminou create_followup_question_elaboration_data em {time.time() - self.start_time} {'-' * 20}")
        print(f"{'>' * 20} Com as seguintes colunas {df.columns} {'<' * 20} \n\n")

    def create_followup_cards_upload_data(self, filename):
        
        print(f"{'*' * 20} Iniciou create_followup_cards_upload_data {'*' * 20}")
        
        df_applications = (
            pl.scan_parquet(f'{self.save_path}/applications.parquet')
            .select('application_id', 'applied', 'deadline_for_sending_response_letters')
            .filter(
                pl.col('applied') == True, 
                pl.col('deadline_for_sending_response_letters').dt.date() >= self.days_after.date()
            )
            .unique()
        )

        df_school_classes = (
            pl.scan_parquet(f'{self.save_path}/school_classes.parquet')
            .select('classe_id', 'classe_name')
            .unique()
        )
        
        df_applications_student = (
            pl.scan_parquet(f'{self.save_path}/applications_student.parquet')
            .join(df_applications.select('application_id'), on='application_id', how='semi')
            .join(df_applications.select('application_id', 'deadline_for_sending_response_letters'), on='application_id', how='inner')
            .join(df_school_classes, on='classe_id', how='inner')
            .filter(
                pl.col('classe_id').is_not_null(),
                pl.col('missed') == False,
            )
            .rename({
                'deadline_for_sending_response_letters': 'deadline'
            })
            .select(
                'application_student_id', 
                'exam_id', 
                'deadline', 
                'classe_id', 
                'classe_name', 
                'unity_id', 
                'objective_pages_sent_count',
                'discursive_pages_sent_count'
            )
        )
        
        df_classes = (
            df_applications_student
            .group_by('classe_id', 'classe_name')
            .agg()
        )
        
        df_exams_questions_count = (
            pl.scan_parquet(f'{self.save_path}/exam_questions.parquet').filter(
                pl.col('is_available') == True,
            )
            .select('exam_question_id', 'exam_id', 'question_category', 'quantity_lines')
            .group_by('exam_id')
            .agg(
                pl.col('exam_question_id').filter(pl.col('question_category').is_in([1, 3])).count().alias('questions_objectives_availables_count'),
                pl.col('exam_question_id').filter(pl.col('question_category').is_in([0, 2])).count().alias('questions_discursives_availables_count'),
                pl.col('quantity_lines').filter(pl.col('question_category') == 0).sum().alias('total_discursive_lines'),
            )
            .with_columns(
                pl.when(pl.col('questions_objectives_availables_count') > 0).then(pl.lit(True)).otherwise(pl.lit(False)).alias('has_objectives'),
                pl.when(pl.col('questions_discursives_availables_count') > 0).then(pl.lit(True)).otherwise(pl.lit(False)).alias('has_discursives'),
            )
            .unique('exam_id')
        )
        
        df_applications_student_with_deadlines = (
            df_applications_student
            .group_by(['deadline', 'exam_id', 'classe_id', 'unity_id'])
            .agg([
                pl.col('objective_pages_sent_count').sum().alias('objective_pages_sent_sum'),
                pl.col('discursive_pages_sent_count').sum().alias('discursive_pages_sent_sum'),
                pl.col('application_student_id').count().alias('applications_students_count'),
            ])
            .with_columns([
                (pl.col('applications_students_count') * pl.col('objective_pages_sent_sum')).alias('objectives_answers_total'),
                (pl.col('applications_students_count') * pl.col('discursive_pages_sent_sum')).alias('discursives_answers_total')
            ])
            .join(df_exams_questions_count, on='exam_id', how='inner')
            .with_columns(
                pl.when(pl.col('has_objectives') == True).then(pl.col('applications_students_count')).otherwise(pl.lit(0)).alias('objectives_pages_predict'),
                pl.when(pl.col('has_discursives') == True).then((pl.col('total_discursive_lines') / LINES_PER_PAGE).ceil() * pl.col('applications_students_count')).otherwise(pl.lit(0)).alias('discursive_pages_predict'),
            )
            .with_columns([
                pl.when(pl.col('objective_pages_sent_sum') > pl.col('objectives_pages_predict')).then(pl.col('objectives_pages_predict')).otherwise(pl.col('objective_pages_sent_sum')).alias('objective_pages_sent_sum'),
                pl.when(pl.col('discursive_pages_sent_sum') > pl.col('discursive_pages_predict')).then(pl.col('discursive_pages_predict')).otherwise(pl.col('discursive_pages_sent_sum')).alias('discursive_pages_sent_sum'),
            ])
            .unique()
        )
        
        df_unities = (
            pl.scan_parquet(f'{self.save_path}/unities.parquet')
        )
        
        df_exams = (
            pl.scan_parquet(f'{self.save_path}/exams.parquet')
            .join(df_unities, on='unity_id', how='inner')
            .select('exam_id', 'unity_id', 'unity_name', 'exam_name', 'teaching_stage_id', 'teaching_stage_name', 'education_system_id', 'education_system_name')
            .unique()
        )
        
        df = (
            df_applications_student_with_deadlines
            .join(df_exams, on=['exam_id', 'unity_id'], how='inner')
            .join(df_classes, on='classe_id', how='inner')
            .collect()
        )
        
        # df.write_csv(f'{self.save_path}/{filename}.csv') # Utilizado apenas para teste
        df.write_parquet(f'{self.save_path}/{filename}.parquet')
        
        print(f"{'-' * 20} Terminou create_followup_cards_upload_data em {time.time() - self.start_time} {'-' * 20}")
        print(f"{'>' * 20} Com as seguintes colunas {df.columns} e {'<' * 20} \n\n")
        
    def create_followup_reviews_data(self, filename):

        print(f"{'*' * 20} Iniciou create_followup_reviews_data {'*' * 20}")

        df_unities = (
            pl.scan_parquet(f'{self.save_path}/unities.parquet')
        )
        
        df_school_classes = (
            pl.scan_parquet(f'{self.save_path}/school_classes.parquet')
            .select('classe_id', 'grade_id')
            .unique()
        )
                
        # Cadernos filtrados
        df_exams = (
            pl.scan_parquet(f'{self.save_path}/exams.parquet')
            .join(df_unities, on='unity_id', how='inner')
            .filter(
                ~pl.col('exam_name').str.to_lowercase().str.contains('bolsa'),
                (pl.col('status') != Exam.CLOSED),
                (pl.col('category') != Exam.HOMEWORK),
                (pl.col('review_deadline').is_not_null()),
                (pl.col('review_deadline').dt.date() >= self.days_after.date()),
            )
            .select(
                'exam_id', 
                'exam_name',
                'unity_id',
                'unity_name',
                'teaching_stage_id',
                'teaching_stage_name',
                'review_deadline',
            )
            .rename({ 'review_deadline': 'deadline' })
            .unique()
        )
        
        df_exam_questions_count = (
            pl.scan_parquet(f'{self.save_path}/exam_questions.parquet')
            .join(df_exams.select('exam_id'), on='exam_id', how='semi')
            .filter(pl.col('is_available') == True)
            .unique('exam_question_id')
            .group_by('exam_id')
            .agg(
                pl.col('exam_question_id').count().alias('questions_count')
            )
        )
                
        df_exams = (
            df_exams
            .join(df_exam_questions_count, on='exam_id', how='inner')
            .filter(
                (pl.col('questions_count') > 0),
            )
        )
        
        df_teachers = (
            pl.scan_parquet(f'{self.save_path}/teachers.parquet')
            .select('teacher_id', 'is_discipline_coordinator', 'teacher_name', 'user_id', 'is_active', 'subject_id', 'unity_id', 'classe_id', 'has_classes')
            .join(df_school_classes, on='classe_id', how='full')
            .filter(
                pl.col('user_id').is_not_null(),
                pl.col('is_active') == True,
                ~pl.col('teacher_name').str.to_lowercase().str.contains('professor'),
                ~pl.col('teacher_name').str.to_lowercase().str.starts_with('avaliações'),
                ~pl.col('teacher_name').str.to_lowercase().str.starts_with('fund '),
            )
        )
        
        df_teachers_coordinator = (
            df_teachers
            .filter(
                pl.col('is_discipline_coordinator') == True,
            )
            .collect()
        )
                                
        df_status_questions = (
            pl.scan_parquet(f'{self.save_path}/status_questions.parquet')
            .group_by('exam_id', 'user_id')
            .agg(
                pl.col('statusquestion_id').count().alias('status_count')
            )
        )
                        
        df_exam_teacher_subjects = (
            pl.scan_parquet(f'{self.save_path}/exam_teacher_subjects.parquet')
            .join(df_exams.select('exam_id'), on='exam_id', how='semi')
            .select(
                'exam_teacher_subject_id', 'exam_id', 'grade_id', 'teacher_id', 'subject_id', 'reviewed_by_user', 'unity_id'  
            )
        )
                        
        df_exam_teacher_subjects = (
            df_exam_teacher_subjects
            .join(df_exams.select('exam_id', 'questions_count'), on='exam_id', how='inner')
            .join(df_teachers.select('teacher_id', 'user_id').unique(), on='teacher_id', how='inner')
            .select(
                'exam_teacher_subject_id',
                'subject_id',
                'reviewed_by_user',
                'unity_id',
                'exam_id',
                'user_id',
                'teacher_id',
                'questions_count',
                'grade_id',
            )
        )
        
        df_teachers_coordinator_without_classes = (
            df_teachers_coordinator
            .filter(
                pl.col('has_classes') == False
            )
            .join(df_exam_teacher_subjects.collect(), on=['unity_id', 'subject_id'], how='inner')
            .select(
                'teacher_id', 
                'teacher_name', 
                'user_id', 
                'user_id_right', 
                'subject_id', 
                'unity_id', 
                'has_classes', 
                'exam_teacher_subject_id', 
                'reviewed_by_user', 
                'exam_id', 
                'questions_count'
            )
        )
        
        df_teachers_coordinator = (
            df_teachers_coordinator
            .filter(
                pl.col('has_classes') == True
            )
            .join(df_exam_teacher_subjects.collect(), on=['unity_id', 'subject_id', 'grade_id'], how='inner')
            .select(
                'teacher_id', 
                'teacher_name', 
                'user_id', 
                'user_id_right', 
                'subject_id', 
                'unity_id', 
                'has_classes', 
                'exam_teacher_subject_id', 
                'reviewed_by_user', 
                'exam_id', 
                'questions_count'
            )
        )
        
        df_teachers_coordinator = (
            df_teachers_coordinator
            .vstack(df_teachers_coordinator_without_classes)
            .unique()
            .lazy()
        )
        
        # Join para pegar dados sem revisores
        df_without_reviewers = (
            df_teachers_coordinator
            .unique()
            .filter(
                (pl.col('reviewed_by_user').is_null() & (pl.col('user_id_right') != pl.col('user_id'))),
            )
            .select(
                'user_id', 
                'user_id_right',
                'teacher_id', 
                'teacher_name',
                'exam_teacher_subject_id',
                'exam_id', 
                'unity_id',
                'subject_id',
                'questions_count',
            )   
        )
                
        # Join para pegar dados com revisores
        df_with_reviewers = (
            df_teachers_coordinator
            .filter(
                (pl.col('reviewed_by_user').is_not_null() & (pl.col('user_id_right') != pl.col('user_id')))
            )
            .select([
                'user_id', 
                'user_id_right',
                'teacher_id', 
                'teacher_name',
                'exam_teacher_subject_id',
                'exam_id', 
                'unity_id',
                'subject_id',
                'questions_count',
            ])   
        )
                
        # União dos dois conjuntos
        df_result = pl.concat([df_with_reviewers, df_without_reviewers])

        df_result = (
            df_result
            .join(df_status_questions, on=['exam_id', 'user_id'], how='left')
            .with_columns(
                pl.col('status_count').fill_null(0).alias('revieweds')
            )
        )

        # Adicionando dados de 'revieweds' via join
        df_final = (
            df_result
            .join(df_unities, on='unity_id', how='inner')
            .join(
                df_exams
                .select(
                    'exam_id', 
                    'unity_id', 
                    'deadline', 
                    'exam_name', 
                    'unity_name', 
                    'teaching_stage_id', 
                    'teaching_stage_name'
                ), 
                on=['exam_id', 'unity_id'], 
                how='inner'
            )
            .select([
                'deadline',
                'exam_id',
                'exam_name',
                'unity_id',
                'unity_name',
                'user_id',
                'subject_id',
                'teacher_id',
                'teacher_name',
                'teaching_stage_id',
                'teaching_stage_name',
                'questions_count',
                'revieweds',
            ])
            .unique()
            .collect()
        )

        # Salva os dados
        # df_final.write_csv(f'{self.save_path}/{filename}.csv')
        df_final.write_parquet(f'{self.save_path}/{filename}.parquet')
        print(f"até aqui demorou: {time.time() - self.start_time} para salvar em parquet com as seguintes colunas: {df_final.columns}")
    
    def create_followup_corrections_data(self, filename):
        print(f"{'*' * 20} Iniciou create_followup_cards_corrections_data {'*' * 20}")
        
        df_applications = (
            pl.scan_parquet(f'{self.save_path}/applications.parquet')
            .filter(
                pl.col('applied') == True,
                pl.col('deadline_for_correction_of_responses').dt.date() >= self.days_after.date(),
            )
            .rename({
                'deadline_for_correction_of_responses': 'deadline',
            })
            .select('application_id', 'deadline', 'exam_id', 'classe_id')
            .unique()
        )
        
        df_school_classes = (
            pl.scan_parquet(f'{self.save_path}/school_classes.parquet')
            .group_by('classe_id', 'classe_name', 'unity_id')
            .agg()
            .unique()
        )
        
        df_applications_student = (
            # pl.scan_parquet(f'{self.save_path}/applications_student.parquet')
            self.get_removed_not_started_applications_student_data()
            .join(
                df_applications.select('application_id'), on='application_id', how='semi'
            )
            .filter(
                pl.col('classe_id').is_not_null(),
                ~pl.col('missed'),
                # pl.col('unity_id') == '51a8989f-f8a3-4797-87bd-e5f7045c89a8',
            )
            .select(
                'application_student_id', 'application_id', 'exam_id', 'classe_id',
            )
            .join(df_school_classes, on='classe_id', how='inner')
            .select(
                'application_student_id', 
                'application_id',
                'exam_id', 
                'classe_id', 
                'unity_id'
            )
            .unique()
        )
        
        df_questions_availables = (
            pl.scan_parquet(f'{self.save_path}/exam_questions.parquet')
            .filter(
                pl.col('is_available'),
                pl.col('weight') > 0,
            )
        )
        
        df_answers = (
            pl.scan_parquet(f'{self.save_path}/answers.parquet')
            .select(
                'answer_id',
                'exam_id',
                'question_id',
                'application_student_id',
                'answered',
            )
            .join(
                df_applications_student, 
                on='application_student_id', 
                how='inner'
            )
            .join( # Deixa respostas availables
                df_questions_availables.select(
                    'question_id', 
                    'question_category'
                ), 
                on='question_id', 
                how='inner'
            )
            .filter(pl.col('answered'))
            .select(
                'application_student_id',
                'answer_id', 
                'exam_id', 
                'question_category', 
                'classe_id', 
                'unity_id'
            )
            .unique()
        )
        
        df_exams_questions_count = (
            df_questions_availables
            .join(df_applications_student.select('exam_id').unique(), on='exam_id', how='semi')
            .group_by('exam_id')
            .agg([
                pl.col('exam_question_id').filter(pl.col('question_category').is_in([1, 3])).count().fill_nan(0).fill_null(0).alias('questions_objectives_availables_count'),
                pl.col('exam_question_id').filter(pl.col('question_category').is_in([0, 2])).count().fill_nan(0).fill_null(0).alias('questions_discursives_availables_count'),
            ])
        )
        
        df_inspectors = (
            pl.scan_parquet(f'{self.save_path}/teachers.parquet')
            .unique(subset=[
                'teacher_id', 
                'subject_id', 
                'classe_id', 
                'unity_id'
            ])
        )
        
        df_inspectors_to_pendences = (
            df_inspectors
            .filter(
                pl.col('user_id').is_not_null(),
                pl.col('is_active'),
                pl.col('classe_id').is_not_null(),
                ~pl.col('teacher_name').str.to_lowercase().str.contains('professor'),
                ~pl.col('teacher_name').str.to_lowercase().str.starts_with('avaliações'),
                ~pl.col('teacher_name').str.to_lowercase().str.starts_with('fund '),
            )
        )
        
        teachers_and_subjects_and_classes = (
            df_inspectors_to_pendences
            .group_by('subject_id', 'teacher_id', 'classe_id', 'unity_id')
            .agg()
        )
        
        df_exam_teacher_subjects = (
            pl.scan_parquet(f'{self.save_path}/exam_teacher_subjects.parquet')
            .select('teacher_id', 'subject_id', 'exam_id', 'unity_id')
            .join(
                df_inspectors.select('teacher_id', 'classe_id'), on='teacher_id', how='inner'
            )
            .unique(subset=[
                'exam_id',
                'unity_id',
                'teacher_id',
                'subject_id',
                'classe_id',
            ])
        )
        
        df_unities = (
            pl.scan_parquet(f'{self.save_path}/unities.parquet')
            .group_by(['unity_id', 'unity_name'])
            .agg()
        )
        
        df_exams = (
            pl.scan_parquet(f'{self.save_path}/exams.parquet')
            .filter(
                ~pl.col('exam_name').str.to_lowercase().str.contains('bolsa')
            )
            .join(df_unities, on='unity_id', how='inner')
            .join(df_exams_questions_count, on='exam_id', how='inner')
            .join(df_applications.select('exam_id', 'classe_id').unique(), on='exam_id', how='inner')
            .join(df_exam_teacher_subjects.select('exam_id', 'teacher_id', 'subject_id'), on=['exam_id', 'teacher_id'], how='inner')
            .select(
                'unity_id', 
                'unity_name', 
                'teaching_stage_id', 
                'education_system_id', 
                'exam_id', 
                'classe_id',
                'subject_id',
                'exam_name', 
                'teacher_id', 
                'teacher_name',
                'teaching_stage_name', 
                'education_system_name', 
                'questions_objectives_availables_count', 
                'questions_discursives_availables_count',
            )
            .unique(subset=[
                'unity_id',
                'exam_id',
                'classe_id',
                'teacher_id',
            ])
        )
        
        df_applications_student_with_exams_and_deadlines = (
            df_applications_student
            .join(
                df_exams.select(
                    'exam_id', 
                    'questions_objectives_availables_count', 
                    'questions_discursives_availables_count'
                ).unique('exam_id'), 
                on='exam_id', 
                how='inner'
            )
            .unique()
        )
        
        df_applications_student_with_deadlines = (
            df_applications_student_with_exams_and_deadlines
            # .filter(
            #     pl.col('exam_id') == 'f9d0d0dc-c2bb-4411-99ee-9eaefa7bb668',
            #     pl.col('classe_id') == '3c9eb4cb-08d4-4f11-b09b-48906e8c6a81'
            # )
            .join(
                df_applications.select('application_id', 'deadline').group_by(['application_id', 'deadline']).agg().unique(),
                on='application_id',
                how='inner'
            )
            .group_by([
                'deadline', 
                'exam_id', 
                'classe_id', 
                'unity_id', 
                'questions_objectives_availables_count', 
                'questions_discursives_availables_count'
            ])
            .agg(
                pl.col('application_student_id').count().alias('applications_students_count'),
            )
            .with_columns([
                (pl.col('applications_students_count') * pl.col('questions_objectives_availables_count')).alias('objectives_answers_total'),
                (pl.col('applications_students_count') * pl.col('questions_discursives_availables_count')).alias('discursives_answers_total')
            ])
            .unique()
        )
        
        df_answers_with_answers_total = (
            df_answers
            # .filter(
            #     pl.col('exam_id') == 'f9d0d0dc-c2bb-4411-99ee-9eaefa7bb668',
            #     pl.col('classe_id') == '3c9eb4cb-08d4-4f11-b09b-48906e8c6a81'
            # )
            .select('exam_id', 'classe_id', 'unity_id', 'answer_id', 'question_category')
            .group_by([
                'exam_id', 
                'classe_id', 
                'unity_id'
            ])
            .agg([
                pl.col('answer_id').filter(pl.col('question_category').is_in([1, 3])).count().alias('objectives_answereds_total'),
                pl.col('answer_id').filter(pl.col('question_category').is_in([0, 2])).count().alias('discursives_answereds_total')
            ])
        )
        
        df_applications_student_with_deadlines = (
            df_applications_student_with_deadlines
            .join(df_answers_with_answers_total, on=['exam_id', 'classe_id', 'unity_id'], how='left')
            .with_columns(
                pl.col('objectives_answereds_total').fill_nan(0).fill_null(0),
                pl.col('discursives_answereds_total').fill_nan(0).fill_null(0),
            )
            .with_columns([
                pl.when(
                    pl.col('objectives_answereds_total') > pl.col('objectives_answers_total')
                ).then(
                    pl.col('objectives_answers_total')
                ).otherwise(
                    pl.col('objectives_answereds_total')
                ).alias('objectives_answereds_total'),
                pl.when(
                    pl.col('discursives_answereds_total') > pl.col('discursives_answers_total')
                ).then(
                    pl.col('discursives_answers_total')
                ).otherwise(
                    pl.col('discursives_answereds_total')
                ).alias('discursives_answereds_total'),
            ])
        )
        
        df = (
            df_applications_student_with_deadlines
            .join(
                df_school_classes.select('classe_id', 'classe_name'), on='classe_id', how='inner'
            )
            .join(
                df_exams.select(
                    'exam_id', 
                    'subject_id', 
                    'exam_name', 
                    'unity_id',
                    'unity_name', 
                    'teaching_stage_id', 
                    'teaching_stage_name', 
                    'education_system_id', 
                    'education_system_name'
                ).unique(), 
                on=[
                    'exam_id', 
                    'unity_id',
                ], 
                how='inner',
            )
            .join(
                teachers_and_subjects_and_classes, on=['subject_id', 'classe_id'], how='inner'
            )
            .join(df_inspectors.select('teacher_id', 'teacher_name').unique('teacher_id'), on='teacher_id', how='inner')
            .select([
                'deadline',
                'exam_id',
                'exam_name',
                'classe_id',
                'classe_name',
                'unity_id',
                'unity_name',
                'teacher_id',
                'teacher_name',
                'objectives_answereds_total',
                'discursives_answereds_total',
                'objectives_answers_total',
                'discursives_answers_total',
                'teaching_stage_id',
                'teaching_stage_name',
                'education_system_id',
                'education_system_name',
            ])
            .unique()
            .collect()
        )
        
        # df.write_csv(f'{self.save_path}/{filename}.csv') # Utilizado apenas para teste
        df.write_parquet(f'{self.save_path}/{filename}.parquet')
        print(f"até aqui demorou: {time.time() - self.start_time} para salvar em parquet com as seguintes colunas: {df.columns}")