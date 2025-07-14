import os

import pyarrow as pa
import pandas as pd
import pyarrow.parquet as pq

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
    help = 'Exporta todas as respostas da GAE2 para o bigquery'

    exams_pks = [
        'eec6f57c-8275-4640-9a80-6cb6ff16ebc0',
        'bb5b03e8-9ada-4df1-9dcb-9c90ba5a1535',
        'd493a09b-930f-4231-82b8-c3ba5296e9fe',
        '86ef1203-d65d-4ad2-8a3e-67b9313ee9a7',
        'cb3d59db-08df-4d87-9723-6124f6158d37',
        'a1fc67df-6302-4101-849c-2b311c461ce5',
        '31408df5-6138-4ae2-937b-7ef43453a63a',
        '46751687-e4a9-47e1-a9de-8e9c3b790941',
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

        # df['exam_name'] = df['exam_name'].str.replace(
        #     'GAE - GARANTIA DE APRENDIZAGENS ESSENCIAIS - ', '', regex=False
        # )
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

    def _save_applicationstudents_to_parquet(self, queryset, filename):
        df = pd.json_normalize(list(queryset))
        df = df.astype({"id": str})
        df = df.astype({"student_id": str})
        df['grade_name'] = df['grade_name'].astype(str) + ' ano'
        # df['exam_name'] = df['exam_name'].str.replace(
        #         'GAE - GARANTIA DE APRENDIZAGENS ESSENCIAIS - ', '', regex=False
        #     )

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

    
    def handle(self, *args, **kwargs):
        tmp_directory = os.path.join('tmp', 'parquet')
        os.makedirs(tmp_directory, exist_ok=True)

        print(f'Processando respostas da GAE2')

        option_answers = self.get_option_answers()
        option_answers_filename = os.path.join(tmp_directory, '5bbe72b2-7a16-4f8c-969f-554a67719c87_optionanswers.parquet')
        self._save_optionanswers_to_parquet(option_answers, option_answers_filename)
        print(f'- {option_answers.count()} option_answers processadas')

        exam_questions = self.get_exam_questions()
        exam_questions_filename = os.path.join(tmp_directory, '5bbe72b2-7a16-4f8c-969f-554a67719c87_examquestions.parquet')
        self._save_examquestions_to_parquet(exam_questions, exam_questions_filename)
        print(f'- {exam_questions.count()} exam questions processadas')

        application_students = self.get_application_students()
        application_students_filename = os.path.join(tmp_directory, '5bbe72b2-7a16-4f8c-969f-554a67719c87_applicationstudents.parquet')
        self._save_applicationstudents_to_parquet(application_students, application_students_filename)
    
        answers_remote_name = 'parquet/gae2/answers_5bbe72b2-7a16-4f8c-969f-554a67719c87.parq'
        storage_service.upload_file(option_answers_filename, answers_remote_name)
        print("Arquivo parquet de respostas enviado para o google cloud storage")

        questions_remote_name = 'parquet/gae2/questions_5bbe72b2-7a16-4f8c-969f-554a67719c87.parq'
        storage_service.upload_file(exam_questions_filename, questions_remote_name)
        print("Arquivo parquet de questões enviado para o google cloud storage")

        applicationstudents_remote_name = 'parquet/gae/applicationstudents_5bbe72b2-7a16-4f8c-969f-554a67719c87.parq'
        storage_service.upload_file(application_students_filename, applicationstudents_remote_name)
        print("Arquivo parquet de application students enviado para o google cloud storage")

        bigquery_service.load_from_parquet(
            answers_remote_name,
            'fiscallize.gae2.answers_5bbe72b2-7a16-4f8c-969f-554a67719c87'
        )

        bigquery_service.load_from_parquet(
            questions_remote_name,
            'fiscallize.gae2.examquestions_5bbe72b2-7a16-4f8c-969f-554a67719c87'
        )

        bigquery_service.load_from_parquet(
            applicationstudents_remote_name,
            'fiscallize.gae2.applicationstudents_5bbe72b2-7a16-4f8c-969f-554a67719c87'
        )
        print("Datasets criados no Bigquery")

        os.remove(option_answers_filename)
        os.remove(exam_questions_filename)
        os.remove(application_students_filename)
        print("Arquivos parquet locais removidos")
