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
from fiscallizeon.bncc.models import Abiliity, Competence
from fiscallizeon.core.gcp import storage_service
from fiscallizeon.core.gcp import bigquery_service

class Command(BaseCommand):
    help = 'Exporta todas as respostas da GAE para o bigquery'

    exams_pks = [
        'c6ec523f-1849-43dd-a919-045d002a9fb3',
        '76fdc6fb-1253-40b2-b219-06865714c72d',
        '8aad154c-2aa3-46e4-8bfe-e57e7462fccb',
        'a9ed00e4-590d-45f1-b2c4-52c1c7a0bdb8',
        '11c6cf98-b7e5-4bcb-82e2-b52780db61eb',
        '8017e86e-a0d4-4761-b929-1f1e25482713',
        '0e2e7fd2-267b-4a90-a206-a1a95e6c420c',
        '2ba478c7-f94f-4914-a828-d238dd448dc1',
        'ba7131a5-e50b-4fa1-89ae-83989e4af797',
        'ec04a776-18ad-4acd-abab-01a1b038cda3',
        '1e661aac-4aa2-4102-8755-8ee329674144',
        'd49c9a80-9cc7-42c4-83ae-efc7319caf0d',
        'c8b54eb4-91b5-476d-8ce0-1770421b760d',
        'a9b97af2-7cc1-41da-a34f-0c4803a0762d',
        '43dfe1cb-745f-46e8-a472-ab6910146810',
        '5a6d820d-3b78-4cdd-9e19-d2bdf763cf00',
        'dd9c4ed6-e85c-4695-8311-db0e2e5c7956',
        '1bf717c9-4b6e-4f63-a2a8-f3f49eceda85',
        '86e2f9e9-3361-4f13-a20f-6896278b6942',
        'aa803237-6c8a-4c28-af23-522a7e810bd1',
        '3148dc74-0553-4a0c-8595-3b6dd1be6916',
        '675ebac3-e437-4974-aad2-90ba42474ede',
        'c206df1a-df84-46ca-bd17-a5074d707297',
        '0ab491f6-81fe-4919-85d0-d1729395554a',
        'c845b6d1-e0c3-48f0-97e6-d25f92680f89'
    ]

    def _save_optionanswers_to_parquet(self, queryset, filename):
        df = pd.json_normalize(list(queryset))
        df = df.astype({"id": str})
        df = df.astype({"student_id": str})
        df = df.astype({"question_id": str})
        df = df.astype({"exam_id": str})
        df = df.astype({"knowledge_area_id": str})
        df = df.astype({"weight": float})
        df = df.astype({"grade": float})
        df['grade_name'] = df['grade_name'].astype(str) + ' ano'
        df['school_class_name'] = df['school_class_name']
        df['question_order'] = df['question_order'] + 1

        df['exam_name'] = df['exam_name'].str.replace(
            'GAE - GARANTIA DE APRENDIZAGENS ESSENCIAIS - ', '', regex=False
        )        
        df['knowledge_area_name'] = df['knowledge_area_name'].str.replace(
            ' - Ensino Fundamental', '', regex=False
        )

        schema = pa.schema([
            ('id', pa.string()),
            ('student_id', pa.string()),
            ('student_name', pa.string()),
            ('question_id', pa.string()),
            ('weight', pa.float64()),
            ('grade', pa.float64()),
            ('subject_order', pa.int8()),
            ('question_order', pa.int8()),
            ('subject_name', pa.string()),
            ('knowledge_area_name', pa.string()),
            ('knowledge_area_id', pa.string()),
            ('exam_id', pa.string()),
            ('exam_name', pa.string()),
            ('school_class_name', pa.string()),
            ('grade_name', pa.string()),
            ('unity_name', pa.string()),
        ])

        table = pa.Table.from_pandas(df, schema=schema, preserve_index=True)
        pq.write_table(table, filename, compression='gzip')

    def _save_examquestions_to_parquet(self, queryset, filename):
        df = pd.json_normalize(list(queryset))
        df = df.astype({"id": str})
        df = df.astype({"question_id": str})
        df = df.astype({"knowledge_area_id": str})
        df = df.astype({"exam_id": str})
        df = df.astype({"weight": float})

        df['knowledge_area_name'] = df['knowledge_area_name'].str.replace(
            ' - Ensino Fundamental', '', regex=False
        )

        topic_schema = pa.list_( 
            pa.struct([
                ('id', pa.string()),
                ('name', pa.string())
            ])
        )

        ability_schema = pa.list_( 
            pa.struct([
                ('code', pa.string()),
                ('text', pa.string())
            ])
        )

        competence_schema = pa.list_( 
            pa.struct([
                ('code', pa.string()),
                ('text', pa.string())
            ])
        )

        schema = pa.schema([
            ('id', pa.string()),
            ('question_id', pa.string()),
            ('exam_id', pa.string()),
            ('weight', pa.float64()),
            ('subject_order', pa.int8()),
            ('order', pa.int8()),
            ('subject_name', pa.string()),
            ('knowledge_area_name', pa.string()),
            ('knowledge_area_id', pa.string()),
            ('topics', topic_schema),
            ('abilities', ability_schema),
            ('competences', competence_schema),
        ])

        table = pa.Table.from_pandas(df, schema=schema, preserve_index=True)
        pq.write_table(table, filename, compression='gzip')

    def _save_tri_to_parquet(self, df, filename):
        df['knowledge_area_name'] = df['knowledge_area_name'].str.replace(
            ' - Ensino Fundamental', '', regex=False
        )

        schema = pa.schema([
            ('student_id', pa.string()),
            ('knowledge_area_id', pa.string()),
            ('knowledge_area_name', pa.string()),
            ('grade', pa.float64()),
        ])

        table = pa.Table.from_pandas(df, schema=schema, preserve_index=True)
        pq.write_table(table, filename, compression='gzip')

    def _save_applicationstudents_to_parquet(self, queryset, filename):
        df = pd.json_normalize(list(queryset))
        df = df.astype({"id": str})
        df = df.astype({"student_id": str})
        df['grade_name'] = df['grade_name'].astype(str) + ' ano'
        df['exam_name'] = df['exam_name'].str.replace(
                'GAE - GARANTIA DE APRENDIZAGENS ESSENCIAIS - ', '', regex=False
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
            ('missed', pa.bool_()),
            ('feedback_after_clean', pa.string()),
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
            knowledge_area_id=Subquery(
                ExamQuestion.objects.filter(
                    Q(exam=OuterRef('student_application__application__exam')),
                    Q(question=OuterRef('question_option__question')),
                ).values(
                    'exam_teacher_subject__teacher_subject__subject__knowledge_area__id'
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
            "question_order", "subject_name", "knowledge_area_name", "knowledge_area_id", "exam_id",  
            "exam_name", "school_class_name", "grade_name", "unity_name")

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
            knowledge_area_id=Case(
                When(
                    exam__is_abstract=False, 
                    then=F('exam_teacher_subject__teacher_subject__subject__knowledge_area_id')
                ),
                default=F('question__subject__knowledge_area_id')
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
            abilities=ArraySubquery(
                Abiliity.objects.filter(question=OuterRef('question')).values(
                    json=JSONObject(code='code', text='text')
                ).distinct()
            ),
            competences=ArraySubquery(
                Competence.objects.filter(question=OuterRef('question')).values(
                    json=JSONObject(code='code', text='text')
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
            "id", "question_id", "exam_id", "weight", "order", "subject_order", 
            "subject_name", "knowledge_area_name", "knowledge_area_id", "topics",
            "abilities", "competences"
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
            'is_attendant', 'missed', 'feedback_after_clean')

    def compute_tri(self, answers_df, std=50, avg=250):
        answers = answers_df.filter(['student_id', 'question_id', 'is_correct'], axis=1)

        answers_pivot = answers.pivot(
            index='question_id',
            columns='student_id',
            values='is_correct'
        ).fillna(False)

        single_student = len(answers_pivot.columns) == 1
        if single_student:
            answers_pivot['F'] = False

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

        if single_student:
            students.drop(['F'], inplace=True)

        return students[['grade']]

    def handle(self, *args, **kwargs):
        tmp_directory = os.path.join('tmp', 'parquet')
        os.makedirs(tmp_directory, exist_ok=True)

        print(f'Processando respostas da GAE')

        option_answers = self.get_option_answers()
        option_answers_filename = os.path.join(tmp_directory, '5bbe72b2-7a16-4f8c-969f-554a67719c87_optionanswers.parquet')
        self._save_optionanswers_to_parquet(option_answers, option_answers_filename)
        print(f'- {option_answers.count()} option_answers processadas')

        exam_questions = self.get_exam_questions()
        exam_questions_filename = os.path.join(tmp_directory, '5bbe72b2-7a16-4f8c-969f-554a67719c87_examquestions.parquet')
        self._save_examquestions_to_parquet(exam_questions, exam_questions_filename)
        print(f'- {exam_questions.count()} exam questions processadas')
    
        answers_remote_name = 'parquet/gae/answers_5bbe72b2-7a16-4f8c-969f-554a67719c87.parq'
        storage_service.upload_file(option_answers_filename, answers_remote_name)
        print("Arquivo parquet de respostas enviado para o google cloud storage")

        questions_remote_name = 'parquet/gae/questions_5bbe72b2-7a16-4f8c-969f-554a67719c87.parq'
        storage_service.upload_file(exam_questions_filename, questions_remote_name)
        print("Arquivo parquet de questões enviado para o google cloud storage")

        bigquery_service.load_from_parquet(
            answers_remote_name,
            'fiscallize.gae.answers_5bbe72b2-7a16-4f8c-969f-554a67719c87'
        )

        bigquery_service.load_from_parquet(
            questions_remote_name,
            'fiscallize.gae.examquestions_5bbe72b2-7a16-4f8c-969f-554a67719c87'
        )
        print("Datasets criados no Bigquery")

        ### Cálculo de TRI
        answers_df = pd.read_parquet(option_answers_filename, engine='pyarrow')
        answers_df = answers_df.drop_duplicates(subset=['student_id', 'question_id'])
        answers_df['is_correct'] = answers_df['grade'] == answers_df['weight']

        tri_filename = os.path.join(tmp_directory, '5bbe72b2-7a16-4f8c-969f-554a67719c87_tri.parquet')

        grades = ['1 ano', '2 ano', '3 ano', '4 ano', '5 ano', '6 ano', '7 ano', '8 ano', '9 ano']
        knowledge_areas = {
            'bd3cc8d3-e3e2-4448-9374-12280268317b': 'Matemática - Ensino Fundamental',
            '61213d2f-2b53-4a3e-95c4-dbc0d3c2d0bd': 'Ciências Humanas - Ensino Fundamental',
            '11228db6-f401-4ac7-8fd8-e6717bc4e553': 'Linguagens - Ensino Fundamental',
            '76464e6d-af8e-426a-b365-1484add39b49': 'Ciências da Natureza - Ensino Fundamental',
        }

        append_data = False
        for grade in grades:
            for knowledge_area in knowledge_areas.keys():
                tri_df = answers_df.loc[answers_df['grade_name'] == grade]
                tri_df = tri_df.loc[answers_df['knowledge_area_id'] == knowledge_area]

                if tri_df.empty:
                    print(f"{grade} não possui {knowledge_areas[knowledge_area]}")
                    continue

                result_df = self.compute_tri(tri_df, std=50, avg=250)
                result_df['knowledge_area_id'] = knowledge_area
                result_df['knowledge_area_name'] = knowledge_areas[knowledge_area]
                self._save_tri_to_parquet(result_df, tri_filename)
                tri_remote_name = 'parquet/gae/tri_5bbe72b2-7a16-4f8c-969f-554a67719c87.parq'
                storage_service.upload_file(tri_filename, tri_remote_name)
                bigquery_service.load_from_parquet(
                    tri_remote_name,
                    'fiscallize.gae.tri_5bbe72b2-7a16-4f8c-969f-554a67719c87',
                    append=append_data,
                )
                append_data = True

        ### Listagem de alunos presentes e ausentes
        application_students = self.get_application_students()
        application_students_filename = os.path.join(tmp_directory, '5bbe72b2-7a16-4f8c-969f-554a67719c87_applicationstudents.parquet')
        self._save_applicationstudents_to_parquet(application_students, application_students_filename)

        applicationstudents_remote_name = 'parquet/gae/applicationstudents_5bbe72b2-7a16-4f8c-969f-554a67719c87.parq'
        storage_service.upload_file(application_students_filename, applicationstudents_remote_name)
        print("Arquivo parquet de application students enviado para o google cloud storage")

        bigquery_service.load_from_parquet(
            applicationstudents_remote_name,
            'fiscallize.gae.applicationstudents_5bbe72b2-7a16-4f8c-969f-554a67719c87'
        )
        print("Dataset de application students criado no Bigquery")

        os.remove(option_answers_filename)
        os.remove(exam_questions_filename)
        os.remove(tri_filename)
        os.remove(application_students_filename)
        print("Arquivos parquet locais removidos")
