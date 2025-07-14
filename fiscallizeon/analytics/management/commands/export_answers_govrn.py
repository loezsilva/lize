import os
import uuid

import requests
import duckdb
import boto3
import pandas as pd

from django.core.management.base import BaseCommand
from django.db.models import F, Q, Subquery, OuterRef, Case, When, Exists, Value, DecimalField, CharField
from django.db.models.functions import JSONObject
from django.contrib.postgres.expressions import ArraySubquery
from django.conf import settings

from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.answers.models import OptionAnswer
from fiscallizeon.exams.models import ExamQuestion, StatusQuestion
from fiscallizeon.subjects.models import Topic

class Command(BaseCommand):
    help = 'Exporta todas as respostas do GOV RN (3º ano)'

    DB_PATH = "tmp/govrn.db"
    exams_pks = [
        '6c54b9a1-518b-4078-9761-1911d0445e26', #MT
        '883e3dc2-2a1c-4c89-831c-2c007bfc6f46', #LP
    ]

    def __init__(self, *args, **kwargs):
        self.database = duckdb.connect(self.DB_PATH)
        return super(Command, self).__init__(*args, **kwargs)

    def _save_optionanswers_to_duckdb(self, queryset):
        df = pd.json_normalize(list(queryset))
        df = df.astype({"id": str})
        df = df.astype({"student_id": str})
        df = df.astype({"question_id": str})
        df = df.astype({"exam_id": str})
        df = df.astype({"weight": float})
        df = df.astype({"grade": float})
        df['grade_name'] = df['grade_name'].astype(str) + ' serie'
        df['question_order'] = df['question_order'] + 1

        df['school_class_name'] = df['school_class_name'].str.replace(
                '3ª SÉRIE - ', '', regex=False
            )

        print(f'OptionAnswers df shape: {df.shape}')
        self.database.query("CREATE OR REPLACE TABLE option_answers AS SELECT * FROM df")

    def _save_examquestions_to_duckdb(self, queryset):
        df = pd.json_normalize(list(queryset))
        df = df.astype({"id": str})
        df = df.astype({"question_id": str})
        df = df.astype({"exam_id": str})
        df = df.astype({"weight": float})

        print(f'ExamQuestions df shape: {df.shape}')
        self.database.query("CREATE OR REPLACE TABLE exam_questions AS SELECT * FROM df")

    def _save_tri_to_duckdb(self, df):
        self.database.query("CREATE OR REPLACE TABLE students_tri AS SELECT * FROM df")

    def _save_applicationstudents_to_duckdb(self, queryset):
        df = pd.json_normalize(list(queryset))
        df = df.astype({"id": str})
        df = df.astype({"student_id": str})
        df['grade_name'] = df['grade_name'].astype(str) + ' serie'
        df['school_class_name'] = df['school_class_name'].str.replace(
                '3ª SÉRIE - ', '', regex=False
            )
        
        print(f'ApplicationStudents df shape: {df.shape}')
        self.database.query("CREATE OR REPLACE TABLE application_students AS SELECT * FROM df")

    def save_direcs_to_duckdb(self):
        tmp_file = f'/tmp/{uuid.uuid4()}.csv'
        remote_path = 'metabase/govrn/direcs.csv'

        s3 = boto3.session.Session().resource(
            's3', 
            region_name=settings.AWS_REGION_NAME, 
            endpoint_url=settings.AWS_S3_ENDPOINT_URL, 
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID, 
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )

        s3.meta.client.download_file(
            settings.AWS_STORAGE_BUCKET_NAME,
            remote_path,
            tmp_file
        )

        self.database.query(f"CREATE OR REPLACE TABLE direcs AS SELECT * FROM '{tmp_file}'")
        os.remove(tmp_file)

    def get_option_answers(self):
        textual_answers = OptionAnswer.objects.filter(
            student_application__application__exam_id__in=self.exams_pks,
            status=OptionAnswer.ACTIVE,
        ).distinct().annotate(
            student_id=F('student_application__student_id'),
            student_name=F('student_application__student__name'),
            question_id=F('question_option__question_id'),
            weight=Subquery(
                ExamQuestion.objects.filter(
                    exam=OuterRef('student_application__application__exam'),
                    question=OuterRef('question_option__question')
                ).values('weight')[:1],
                output_field=DecimalField()
            ),
            grade=Case(
                When(question_option__is_correct=True, then=F('weight')),
                default=Value(0, output_field=DecimalField())
            ),
            subject_order=Subquery(
                ExamQuestion.objects.filter(
                    Q(exam=OuterRef('student_application__application__exam')),
                    Q(question=OuterRef('question_option__question')),
                ).values(
                    'exam_teacher_subject__order'
                )[:1]
            ),
            question_order=Subquery(
                ExamQuestion.objects.filter(
                    Q(exam=OuterRef('student_application__application__exam')),
                    Q(question=OuterRef('question_option__question')),
                ).values(
                    'order'
                )[:1]
            ),
            subject_name=Subquery(
                ExamQuestion.objects.filter(
                    Q(exam=OuterRef('student_application__application__exam')),
                    Q(question=OuterRef('question_option__question')),
                ).values(
                    'exam_teacher_subject__teacher_subject__subject__name'
                )[:1]
            ),
            knowledge_area_name=Subquery(
                ExamQuestion.objects.filter(
                    Q(exam=OuterRef('student_application__application__exam')),
                    Q(question=OuterRef('question_option__question')),
                ).values(
                    'exam_teacher_subject__teacher_subject__subject__knowledge_area__name'
                )[:1]
            ),
            exam_id=F('student_application__application__exam_id'),
            exam_name=F('student_application__application__exam__name'),
            school_class_name=Subquery(
                SchoolClass.objects.filter(
                    students=OuterRef('student_application__student')
                ).distinct().values(
                    'name'
                )[:1],
                output_field=CharField()
            ),
            grade_name=Subquery(
                SchoolClass.objects.filter(
                    students=OuterRef('student_application__student')
                ).distinct().values(
                    'grade__name'
                )[:1],
                output_field=CharField()
            ),
            unity_name=Subquery(
                SchoolClass.objects.filter(
                    students=OuterRef('student_application__student')
                ).values(
                    'coordination__unity__name'
                ).distinct()[:1],
                output_field=CharField()
            ),
        ).distinct()

        return textual_answers.values(
            "id", "student_id", "student_name", "question_id", "weight", "grade", "subject_order",
            "question_order", "subject_name", "knowledge_area_name", "exam_id", "exam_name", 
            "school_class_name", "grade_name", "unity_name")

    def get_exam_questions(self):
        exam_questions = ExamQuestion.objects.annotate(
            subject_order=F('exam_teacher_subject__order'),
            subject_name=Case(
                When(
                    exam__is_abstract=False, 
                    then=F('exam_teacher_subject__teacher_subject__subject__name')
                ),
                default=F('question__subject__name')
            ),
            knowledge_area_name=Case(
                When(
                    exam__is_abstract=False, 
                    then=F('exam_teacher_subject__teacher_subject__subject__knowledge_area__name')
                ),
                default=F('question__subject__knowledge_area__name')
            ),
            last_examquestion_status=Subquery(
                StatusQuestion.objects.filter(
                    exam_question__question=OuterRef('question'),
                    exam_question__exam=OuterRef('exam'),
                ).order_by('-created_at').values('status')[:1]
            ),
            topics=ArraySubquery(
                Topic.objects.filter(questions=OuterRef('question')).values(
                    json=JSONObject(id='id', name='name')
                ).distinct()
            ),
        ).filter(
            Q(exam__in=self.exams_pks),
            Q(
                Q(last_examquestion_status__isnull=True) |
                ~Q(last_examquestion_status__in=[
                    StatusQuestion.REPROVED,
                    StatusQuestion.ANNULLED
                ])
            )
        ).distinct()

        return exam_questions.values(
            "id", "question_id", "exam_id", "weight", "order",
            "subject_order", "subject_name", "knowledge_area_name", "topics",
        )

    def get_application_students(self):
        application_students = ApplicationStudent.objects.filter(
            application__exam__in=self.exams_pks
        ).annotate(
            student_name=F('student__name'),
            exam_name=F('application__exam__name'),
            school_class_name=Subquery(
                SchoolClass.objects.filter(
                    students=OuterRef('student')
                ).distinct().values(
                    'name'
                )[:1],
                output_field=CharField()
            ),
            grade_name=Subquery(
                SchoolClass.objects.filter(
                    students=OuterRef('student')
                ).distinct().values(
                    'grade__name'
                )[:1],
                output_field=CharField()
            ),
            unity_name=Subquery(
                SchoolClass.objects.filter(
                    students=OuterRef('student')
                ).values(
                    'coordination__unity__name'
                ).distinct()[:1],
                output_field=CharField()
            ),
            is_attendant=Exists(
                OptionAnswer.objects.filter(student_application=OuterRef('pk'))
            )
        )

        return application_students.values(
            'id', 'student_id', 'student_name', 'exam_name', 
            'school_class_name', 'grade_name', 'unity_name', 
            'is_attendant')

    def compute_tri(self, exam_pks):
        response = requests.post(
                f'{settings.ANALYTICS_SERVICE_URL}/tri-saeb',
                json={'exams': exam_pks}
            )
        
        tri_df = pd.DataFrame(response.json())
        tri_df = tri_df[tri_df['correct_count'].notna()]
        return tri_df[['student_id', 'knowledge_area', 'grade']]

    def save_db_on_spaces(self):
        s3 = boto3.session.Session().resource(
            's3', 
            region_name=settings.AWS_REGION_NAME, 
            endpoint_url=settings.AWS_S3_ENDPOINT_URL, 
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID, 
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
        )

        result = s3.meta.client.upload_file(
            Filename=self.DB_PATH,
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=f'metabase/govrn/govrn.db'
        )

        print(result)

    def handle(self, *args, **kwargs):
        tmp_directory = os.path.join('tmp', 'parquet')
        os.makedirs(tmp_directory, exist_ok=True)

        print(f'Processando respostas do GOV RN')

        self.save_direcs_to_duckdb()
        print('Direcs salvas com sucesso')

        option_answers = self.get_option_answers()
        self._save_optionanswers_to_duckdb(option_answers)
        print(f'- {option_answers.count()} option_answers processadas')

        exam_questions = self.get_exam_questions()
        self._save_examquestions_to_duckdb(exam_questions)
        print(f'- {exam_questions.count()} exam questions processadas')

        application_students = self.get_application_students()
        self._save_applicationstudents_to_duckdb(application_students)
        print(f'- {application_students.count()} application students processados')

        tri_df = self.compute_tri(self.exams_pks)
        self._save_tri_to_duckdb(tri_df)
        print("Notas TRI salvas com sucesso")

        self.save_db_on_spaces()
        print("Database salvo no spaces")