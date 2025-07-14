import os

import pyarrow as pa
import pandas as pd
import pyarrow.parquet as pq
from girth import threepl_mml, ability_3pl_eap

from django.core.management.base import BaseCommand
from django.db.models import F, Q, Subquery, OuterRef, Case, When, Exists, Value, DecimalField, CharField
from django.db.models.functions import JSONObject
from django.contrib.postgres.expressions import ArraySubquery

from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.answers.models import OptionAnswer
from fiscallizeon.exams.models import ExamQuestion, StatusQuestion
from fiscallizeon.subjects.models import Topic
from fiscallizeon.core.gcp import storage_service
from fiscallizeon.core.gcp import bigquery_service

class Command(BaseCommand):
    help = 'Exporta todas as respostas da AVHA para o bigquery'

    exams_pks = [
        '3349dfcc-88ef-44b2-9b14-f5ea526acb0d',
        'e7b5e701-a275-4e5b-87a1-637475026b73',
    ]

    def _save_optionanswers_to_parquet(self, queryset, filename):
        df = pd.json_normalize(list(queryset))
        df = df.astype({"id": str})
        df = df.astype({"student_id": str})
        df = df.astype({"question_id": str})
        df = df.astype({"exam_id": str})
        df = df.astype({"grade": float})
        df['grade_name'] = df['grade_name'].astype(str) + ' ano'
        df['exam_name'] = df['exam_name'].str.replace(
                'IDEC - ÍNDICE DE DESENVOLVIMENTO EDUCACIONAL COOPEDU - 01 - ', '', regex=False
            )

        schema = pa.schema([
            ('id', pa.string()),
            ('student_id', pa.string()),
            ('student_name', pa.string()),
            ('question_id', pa.string()),
            ('grade', pa.float64()),
            ('is_correct', pa.bool_()),
            ('question_order', pa.int8()),
            ('subject_name', pa.string()),
            ('exam_id', pa.string()),
            ('exam_name', pa.string()),
            ('school_class_name', pa.string()),
            ('grade_name', pa.string()),
            ('unity_name', pa.string()),
        ])

        table = pa.Table.from_pandas(df, schema=schema, preserve_index=True)
        pq.write_table(table, filename, compression='gzip')

    def _save_tri_to_parquet(self, df, filename):
        schema = pa.schema([
            ('student_id', pa.string()),
            ('subject_name', pa.string()),
            ('grade', pa.float64()),
        ])

        table = pa.Table.from_pandas(df, schema=schema, preserve_index=True)
        pq.write_table(table, filename, compression='gzip')

    def _save_examquestions_to_parquet(self, queryset, filename):
        df = pd.json_normalize(list(queryset))
        df = df.astype({"id": str})
        df = df.astype({"question_id": str})
        df = df.astype({"exam_id": str})
        df = df.astype({"weight": float})

        topic_schema = pa.list_( 
            pa.struct([
                ('id', pa.string()),
                ('name', pa.string())
            ])
        )

        schema = pa.schema([
            ('id', pa.string()),
            ('question_id', pa.string()),
            ('exam_id', pa.string()),
            ('weight', pa.float64()),
            ('order', pa.int8()),
            ('subject_name', pa.string()),
            ('topics', topic_schema),
        ])

        table = pa.Table.from_pandas(df, schema=schema, preserve_index=True)
        pq.write_table(table, filename, compression='gzip')

    def _save_applicationstudents_to_parquet(self, queryset, filename):
        df = pd.json_normalize(list(queryset))
        df = df.astype({"id": str})
        df = df.astype({"student_id": str})
        df['grade_name'] = df['grade_name'].astype(str) + ' ano'
        df['exam_name'] = df['exam_name'].str.replace(
                'IDEC - ÍNDICE DE DESENVOLVIMENTO EDUCACIONAL COOPEDU - 01 - ', '', regex=False
            )

        schema = pa.schema([
            ('id', pa.string()),
            ('student_id', pa.string()),
            ('student_name', pa.string()),
            ('exam_name', pa.string()),
            ('school_class_name', pa.string()),
            ('grade_name', pa.string()),
            ('unity_name', pa.string()),
            ('is_attendant', pa.bool_()),
        ])

        table = pa.Table.from_pandas(df, schema=schema, preserve_index=True)
        pq.write_table(table, filename, compression='gzip')

    def get_option_answers(self):
        option_answers = OptionAnswer.objects.filter(
            student_application__application__exam_id__in=self.exams_pks,
            status=OptionAnswer.ACTIVE,
        ).distinct().annotate(
            student_id=F('student_application__student_id'),
            student_name=F('student_application__student__name'),
            question_id=F('question_option__question_id'),
            grade=Case(
                When(question_option__is_correct=True, then=Value(1.0, output_field=DecimalField())),
                default=Value(0, output_field=DecimalField())
            ),
            is_correct=F('question_option__is_correct'),
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
            "id", "student_id", "student_name", "question_id", "grade",
            "is_correct", "question_order", "subject_name", "exam_id",
            "exam_name", "school_class_name", "grade_name", "unity_name")

    def get_exam_questions(self):
        exam_questions = ExamQuestion.objects.annotate(
            subject_name=F('question__subject__name'),
            topics=ArraySubquery(
                Topic.objects.filter(questions=OuterRef('question')).values(
                    json=JSONObject(id='id', name='name')
                ).distinct()
            ),
        ).filter(
            Q(exam__in=self.exams_pks),
        ).distinct()

        return exam_questions.values(
            "id", "question_id", "exam_id", "weight", "order",
            "subject_name", "topics"
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

    def compute_tri(self, answers_df, std=50, avg=250):
        answers = answers_df.filter(['student_id', 'question_id', 'is_correct'], axis=1)

        answers_pivot = answers.pivot(
            index='question_id',
            columns='student_id',
            values='is_correct'
        ).fillna(False)

        answers_np = answers_pivot.to_numpy()
        parameters = threepl_mml(answers_np)
        averages = ability_3pl_eap(
            answers_np,
            parameters['Difficulty'],
            parameters['Discrimination'],
            parameters['Guessing']
        )

        students = answers_pivot.T
        students['grade'] = averages * std + avg
        return students[['grade']]

    def handle(self, *args, **kwargs):
        tmp_directory = os.path.join('tmp', 'parquet')
        os.makedirs(tmp_directory, exist_ok=True)

        print(f'Processando respostas do IDEC')

        option_answers = self.get_option_answers()
        option_answers_filename = os.path.join(tmp_directory, '43899d53-5721-415e-90c1-68c8ccbaaa62_optionanswers.parquet')
        self._save_optionanswers_to_parquet(option_answers, option_answers_filename)
        print(f'- {option_answers.count()} option_answers processadas')

        exam_questions = self.get_exam_questions()
        exam_questions_filename = os.path.join(tmp_directory, '43899d53-5721-415e-90c1-68c8ccbaaa62_examquestions.parquet')
        self._save_examquestions_to_parquet(exam_questions, exam_questions_filename)
        print(f'- {exam_questions.count()} exam questions processadas')
    
        answers_remote_name = 'parquet/idec/answers_43899d53-5721-415e-90c1-68c8ccbaaa62.parq'
        storage_service.upload_file(option_answers_filename, answers_remote_name)
        print("Arquivo parquet de respostas enviado para o google cloud storage")

        questions_remote_name = 'parquet/idec/questions_43899d53-5721-415e-90c1-68c8ccbaaa62.parq'
        storage_service.upload_file(exam_questions_filename, questions_remote_name)
        print("Arquivo parquet de questões enviado para o google cloud storage")

        bigquery_service.load_from_parquet(
            answers_remote_name,
            'fiscallize.idec.answers_43899d53-5721-415e-90c1-68c8ccbaaa62'
        )

        bigquery_service.load_from_parquet(
            questions_remote_name,
            'fiscallize.idec.examquestions_43899d53-5721-415e-90c1-68c8ccbaaa62'
        )

        print("Datasets criados no Bigquery")

        ### Cálculo de TRI
        answers_df = pd.read_parquet(option_answers_filename, engine='pyarrow')
        answers_df = answers_df.drop_duplicates(subset=['student_id', 'question_id'])

        tri_filename = os.path.join(tmp_directory, '43899d53-5721-415e-90c1-68c8ccbaaa62_tri.parquet')

        subjects = {
            '5 ano': [
                {'name': 'Matemática', 'std': 55.8923279, 'avg': 249.964381},
                {'name': 'Língua Portuguesa', 'std': 55.0933628, 'avg': 249.98499}
            ],
            '9 ano': [
                {'name': 'Matemática', 'std': 55.8923279, 'avg': 249.964381},
                {'name': 'Língua Portuguesa', 'std': 55.0933628, 'avg': 249.98499}
            ]
        }

        append_data = False
        for grade in subjects.keys():
            for subject in subjects[grade]:
                tri_df = answers_df[answers_df['grade_name'] == grade]
                tri_df = tri_df.loc[tri_df['subject_name'] == subject['name']]

                result_df = self.compute_tri(tri_df, std=subject['std'], avg=subject['avg'])
                result_df['subject_name'] = subject['name']
                self._save_tri_to_parquet(result_df, tri_filename)
                tri_remote_name = 'parquet/idec/tri_43899d53-5721-415e-90c1-68c8ccbaaa62.parq'
                storage_service.upload_file(tri_filename, tri_remote_name)
                bigquery_service.load_from_parquet(
                    tri_remote_name,
                    'fiscallize.idec.tri_43899d53-5721-415e-90c1-68c8ccbaaa62',
                    append=append_data
                )
                append_data = True

        ### Listagem de alunos presentes e ausentes
        application_students = self.get_application_students()
        application_students_filename = os.path.join(tmp_directory, '43899d53-5721-415e-90c1-68c8ccbaaa62_applicationstudents.parquet')
        self._save_applicationstudents_to_parquet(application_students, application_students_filename)

        applicationstudents_remote_name = 'parquet/idec/applicationstudents_43899d53-5721-415e-90c1-68c8ccbaaa62.parq'
        storage_service.upload_file(application_students_filename, applicationstudents_remote_name)
        print("Arquivo parquet de application students enviado para o google cloud storage")

        bigquery_service.load_from_parquet(
            applicationstudents_remote_name,
            'fiscallize.idec.applicationstudents_43899d53-5721-415e-90c1-68c8ccbaaa62'
        )
        print("Dataset de application students criado no Bigquery")

        os.remove(option_answers_filename)
        os.remove(exam_questions_filename)
        os.remove(tri_filename)
        os.remove(application_students_filename)
        print("Arquivos parquet locais removidos")
