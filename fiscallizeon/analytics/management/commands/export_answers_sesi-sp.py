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
from fiscallizeon.exams.models import ExamQuestion, StatusQuestion, Exam
from fiscallizeon.bncc.models import Abiliity

class Command(BaseCommand):
    help = 'Exporta todas as respostas do SESI-SP'

    DB_PATH = "tmp/sesisp.db"
    CLIENT_PK = 'c3d45804-f6ff-4865-a755-d41b4a79d32e'

    def __init__(self, *args, **kwargs):
        self.database = duckdb.connect(self.DB_PATH)
        self.exams_pks = [
            '6f5b42b9-b8ab-4703-b8df-bfd0fda292ef', 
            '2f29b483-f09e-4ad1-b428-d713057ce0fb', 
            '4b9e7734-2a2b-4c0d-b50b-2953dece01b5', 
            '3dcae378-834a-491b-b65f-ee0087c13821'
        ]

        self.exams_saeb = Exam.objects.filter(
            Q(pk__in=self.exams_pks),
            # Q(
            #     Q(name__icontains='5º ANO') |
            #     Q(name__icontains='9º ANO')
            # )
        )
        return super(Command, self).__init__(*args, **kwargs)

    def _save_optionanswers_to_duckdb(self, queryset):
        df = pd.json_normalize(list(queryset))
        df = df.astype({"id": str})
        df = df.astype({"student_id": str})
        df = df.astype({"question_id": str})
        df = df.astype({"exam_id": str})
        df = df.astype({"weight": float})
        df = df.astype({"grade": float})
        # df['grade_name'] = df['grade_name'].astype(str) + ' serie'
        # df['knowledge_area_name'] = df['knowledge_area_name'].str.replace(
        #     ' - Ensino Fundamental', '', regex=False
        # )
        # df['unity_name'] = df['unity_name'].str.replace(
        #     ' - SESI SP', '', regex=False
        # )
        df['question_order'] = df['question_order'] + 1

        print(f'OptionAnswers df shape: {df.shape}')
        self.database.query("CREATE OR REPLACE TABLE option_answers AS SELECT * FROM df")

    def _save_examquestions_to_duckdb(self, queryset):
        df = pd.json_normalize(list(queryset))
        df['weight'] = 1.0

        df = df.astype({"id": str})
        df = df.astype({"question_id": str})
        df = df.astype({"exam_id": str})
        df = df.astype({"weight": float})

        # df['knowledge_area_name'] = df['knowledge_area_name'].str.replace(
        #     ' - Ensino Fundamental', '', regex=False
        # )

        print(f'ExamQuestions df shape: {df.shape}')
        self.database.query("CREATE OR REPLACE TABLE exam_questions AS SELECT * FROM df")

    def _save_tri_to_duckdb(self, df):
        df['knowledge_area'] = df['knowledge_area'].str.replace(
            ' - Ensino Fundamental', '', regex=False
        )
        self.database.query("CREATE OR REPLACE TABLE students_tri AS SELECT * FROM df")

    def _save_applicationstudents_to_duckdb(self, queryset):
        df = pd.json_normalize(list(queryset))
        df = df.astype({"id": str})
        df = df.astype({"student_id": str})
        df['grade_name'] = df['grade_name'].astype(str) + ' serie'
        df['unity_name'] = df['unity_name'].str.replace(
            ' - SESI SP', '', regex=False
        )
        print(f'ApplicationStudents df shape: {df.shape}')
        self.database.query("CREATE OR REPLACE TABLE application_students AS SELECT * FROM df")

    def save_cities_to_duckdb(self):
        tmp_file = f'/tmp/{uuid.uuid4()}.csv'
        remote_path = 'metabase/sesi-sp/municipios.csv'

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

        self.database.query(f"CREATE OR REPLACE TABLE municipios AS SELECT * FROM '{tmp_file}'")
        os.remove(tmp_file)

    def get_option_answers(self):
        option_answers = OptionAnswer.objects.filter(
            student_application__application__exam_id__in=self.exams_pks,
            status=OptionAnswer.ACTIVE,
        ).distinct().annotate(
            student_id=F('student_application__student_id'),
            student_name=F('student_application__student__name'),
            question_id=F('question_option__question_id'),
            weight=Value(1, output_field=DecimalField()),
            grade=Case(
                When(question_option__is_correct=True, then=Value(1, output_field=DecimalField())),
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
                    'question__subject__name'
                )[:1]
            ),
            knowledge_area_name=Subquery(
                ExamQuestion.objects.filter(
                    Q(exam=OuterRef('student_application__application__exam')),
                    Q(question=OuterRef('question_option__question')),
                ).values(
                    'question__subject__knowledge_area__name'
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

        return option_answers.values(
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
                Abiliity.objects.filter(question=OuterRef('question')).values(
                    json=JSONObject(id='id', name='text', code='code')
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

    def handle(self, *args, **kwargs):
        tmp_directory = os.path.join('tmp', 'parquet')
        os.makedirs(tmp_directory, exist_ok=True)

        print(f'Processando respostas do SESI-SP')

        self.save_cities_to_duckdb()
        print(f'Municípios atualizados')

        option_answers = self.get_option_answers()
        self._save_optionanswers_to_duckdb(option_answers)
        print(f'- {option_answers.count()} option_answers processadas')

        exam_questions = self.get_exam_questions()
        self._save_examquestions_to_duckdb(exam_questions)
        print(f'- {exam_questions.count()} exam questions processadas')

        application_students = self.get_application_students()
        self._save_applicationstudents_to_duckdb(application_students)
        print(f'- {application_students.count()} application students processados')

        tri_df = pd.DataFrame()
        for exam in self.exams_saeb:
            answers = OptionAnswer.objects.filter(
                student_application__application__exam=exam,
            )

            if not answers.exists():
                continue

            has_correct_answers = answers.filter(
                question_option__is_correct=True,
            )
            has_incorrect_answers = answers.filter(
                question_option__is_correct=False,
            )
            if has_correct_answers and has_incorrect_answers:
                _tri_df = self.compute_tri([str(exam.pk)])
                _tri_df['exam_id'] = str(exam.pk)
                tri_df = pd.concat([tri_df, _tri_df])

        self._save_tri_to_duckdb(tri_df)
        print("Notas TRI salvas com sucesso")