import os

import numpy as np
import pyarrow as pa
import pandas as pd
import pyarrow.parquet as pq

from django.utils import timezone
from django.core.management.base import BaseCommand
from django.db.models.functions import Cast, Coalesce, JSONObject
from django.contrib.postgres.expressions import ArraySubquery
from django.db.models import F, Q, Subquery, OuterRef, Case, When, Value, DecimalField, CharField, UUIDField

from fiscallizeon.classes.models import Client
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.answers.models import OptionAnswer, FileAnswer, TextualAnswer
from fiscallizeon.bncc.models import Abiliity, Competence
from fiscallizeon.subjects.models import Topic
from fiscallizeon.exams.models import ExamQuestion, StatusQuestion, ExamTeacherSubject
from fiscallizeon.core.gcp import storage_service
from fiscallizeon.core.gcp import bigquery_service

class Command(BaseCommand):
    help = 'Exporta todas as respostas de um determinado ano para o o Google Bigquery'

    def add_arguments(self, parser):
        parser.add_argument('--year', nargs=1, type=int, required=False)
        parser.add_argument('--dryrun', action='store_true', default=False, help='Executa sem subir arquivos para GCP')
        parser.add_argument('--schema', action='store_true', default=False, help='Apenas cria arquivo parquet com schema no GCS')

    def _get_pyarrow_schema(self):
        topic_schema = pa.list_( 
            pa.struct([
                ('id', pa.string()),
                ('name', pa.string())
            ])
        )

        bncc_schema = pa.list_(
            pa.struct([
                ('id', pa.string()),
                ('code', pa.string()),
                ('text', pa.string())
            ])
        )

        return pa.schema([
            ('id', pa.string()),
            ('application_date', pa.date64()),
            ('student_name', pa.string()),
            ('student_id', pa.string()),
            ('application_student_id', pa.string()),
            ('question_id', pa.string()),
            ('is_objective', pa.bool_()),
            ('weight', pa.float64()),
            ('grade', pa.float64()),
            ('exam_name', pa.string()),
            ('exam_id', pa.string()),
            ('exam_abstract', pa.bool_()),
            ('subject_id', pa.string()),
            ('subject_name', pa.string()),
            ('knowledge_area_id', pa.string()),
            ('knowledge_area_name', pa.string()),
            ('topics', topic_schema),
            ('abilities', bncc_schema),
            ('competences', bncc_schema),
            ('school_class_name', pa.string()),
            ('school_class_id', pa.string()),
            ('grade_id', pa.string()),
            ('unity_name', pa.string()),
            ('unity_id', pa.string()),
            ('client_name', pa.string()),
            ('client_id', pa.string()),
        ])

    def _save_qs_to_parquet(self, queryset, filename, empty=False):
        df = pd.json_normalize(list(queryset))
        df = df.astype({"id": str})
        df = df.astype({"student_id": str})
        df = df.astype({"application_student_id": str})
        df = df.astype({"question_id": str})
        df = df.astype({"exam_id": str})
        df = df.astype({"school_class_id": str})
        df = df.astype({"subject_id": str})
        df = df.astype({"knowledge_area_id": str})
        df = df.astype({"grade_id": str})
        df = df.astype({"unity_id": str})
        df = df.astype({"client_id": str})
        df = df.astype({"weight": float})
        df = df.astype({"grade": float})

        df['subject_id'] = df['subject_id'].replace('None', 'Geral')
        df['knowledge_area_id'] = df['knowledge_area_id'].replace('None', '0')
        df['knowledge_area_name'] = df['knowledge_area_name'].replace(np.nan, 'Geral')
        df['grade_id'] = df['grade_id'].replace('None', np.nan)
        df['unity_id'] = df['unity_id'].replace('None', np.nan)
        df['school_class_id'] = df['school_class_id'].replace('None', np.nan)

        if empty:
            df = df.drop(df.index)

        schema = self._get_pyarrow_schema()
        table = pa.Table.from_pandas(df, schema=schema, preserve_index=True)
        pq.write_table(table, filename, compression='gzip')

    def _merge_parquet_files(self, file_paths, output_filename):
        file_schemas = [pq.ParquetFile(f).schema_arrow for f in file_paths]
        unified_schemas = pa.unify_schemas(file_schemas)
        with pq.ParquetWriter(output_filename, schema=unified_schemas) as writer:
            for file in file_paths:
                writer.write_table(pq.read_table(file))

    def _create_base_schema_parquet(self, tmp_directory):
        print('Criando parquet schema para bigquery...')
        client = Client.objects.get(pk='a2b1158b-367a-40a4-8413-9897057c8aa2')
        option_answers = self.get_option_answers(client, 2022, 7)
        base_schema_filename = os.path.join(tmp_directory, f'base.parquet')
        self._save_qs_to_parquet(option_answers, base_schema_filename, empty=True)
        return base_schema_filename

    def get_option_answers(self, client, year, month):
        option_answers = OptionAnswer.objects.annotate(
                last_examquestion_status=Subquery(
                    StatusQuestion.objects.filter(
                        exam_question__question=OuterRef('question_option__question'),
                        exam_question__exam=OuterRef('student_application__application__exam'),
                    ).order_by('-created_at').values('status')[:1]
                )
            ).filter(
                Q(student_application__application__exam='56275cdc-ba85-4a2e-a9b0-ed58312faf8f'),
                Q(student_application__student__client=client),
                Q(created_at__year=year),
                Q(created_at__month=month),
                Q(status=OptionAnswer.ACTIVE),
                Q(
                    Q(last_examquestion_status__isnull=True) |
                    ~Q(last_examquestion_status__in=[
                        StatusQuestion.REPROVED,
                        StatusQuestion.ANNULLED
                    ])
                )
            ).annotate(
                application_date=F('student_application__application__date'),
                student_name=F('student_application__student__name'),
                student_id=F('student_application__student_id'),
                application_student_id=F('student_application'),
                question_id=F('question_option__question_id'),
                is_objective=Value(True),
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
                exam_name=F('student_application__application__exam__name'),
                exam_id=F('student_application__application__exam_id'),
                exam_abstract=F('student_application__application__exam__is_abstract'),
                subject_id=Case(
                    When(
                        student_application__application__exam__is_abstract=False, 
                        then=Subquery(
                            ExamTeacherSubject.objects.filter(
                                exam=OuterRef('student_application__application__exam'),
                                examquestion__question=OuterRef('question_option__question')
                            ).distinct().values('teacher_subject__subject_id')[:1],
                            output_field=UUIDField()
                        ),
                    ),
                    default=F('question_option__question__subject_id')
                ),
                subject_name=Case(
                    When(
                        student_application__application__exam__is_abstract=False, 
                        then=Subquery(
                            ExamTeacherSubject.objects.filter(
                                exam=OuterRef('student_application__application__exam'),
                                examquestion__question=OuterRef('question_option__question')
                            ).distinct().values('teacher_subject__subject__name')[:1],
                            output_field=CharField()
                        ),
                    ),
                    default=F('question_option__question__subject__name')
                ),
                knowledge_area_id=Case(
                    When(
                        student_application__application__exam__is_abstract=False, 
                        then=Subquery(
                            ExamTeacherSubject.objects.filter(
                                exam=OuterRef('student_application__application__exam'),
                                examquestion__question=OuterRef('question_option__question')
                            ).distinct().values('teacher_subject__subject__knowledge_area_id')[:1],
                            output_field=UUIDField()
                        ),
                    ),
                    default=F('question_option__question__subject__knowledge_area_id')
                ),
                knowledge_area_name=Case(
                    When(
                        student_application__application__exam__is_abstract=False, 
                        then=Subquery(
                            ExamTeacherSubject.objects.filter(
                                exam=OuterRef('student_application__application__exam'),
                                examquestion__question=OuterRef('question_option__question')
                            ).distinct().values('teacher_subject__subject__knowledge_area__name')[:1],
                            output_field=CharField()
                        ),
                    ),
                    default=F('question_option__question__subject__knowledge_area__name')
                ),
                topics=ArraySubquery(
                    Topic.objects.filter(question=OuterRef('question_option__question')).values(
                        json=JSONObject(id='id', name='name')
                    ).distinct()
                ),
                abilities=ArraySubquery(
                    Abiliity.objects.filter(question=OuterRef('question_option__question')).values(
                        json=JSONObject(id='id', code='code', text='text')
                    ).distinct()
                ),
                competences=ArraySubquery(
                    Competence.objects.filter(question=OuterRef('question_option__question')).values(
                        json=JSONObject(id='id', code='code', text='text')
                    ).distinct()
                ),
                school_class_name=Subquery(
                    SchoolClass.objects.filter(
                        school_year=year,
                        students=OuterRef('student_application__student')
                    ).distinct().values(
                        'name'
                    )[:1],
                    output_field=CharField()
                ),
                school_class_id=Subquery(
                    SchoolClass.objects.filter(
                        school_year=year,
                        students=OuterRef('student_application__student')
                    ).distinct().values(
                        'id'
                    )[:1],
                    output_field=CharField()
                ),
                grade_id=Subquery(
                    SchoolClass.objects.filter(
                        school_year=year,
                        students=OuterRef('student_application__student')
                    ).distinct().values(
                        'grade_id'
                    )[:1],
                    output_field=CharField()
                ),
                unity_name=Subquery(
                    SchoolClass.objects.filter(
                        school_year=year,
                        students=OuterRef('student_application__student')
                    ).values(
                        'coordination__unity__name'
                    ).distinct()[:1],
                    output_field=CharField()
                ),
                unity_id=Subquery(
                    SchoolClass.objects.filter(
                        school_year=year,
                        students=OuterRef('student_application__student')
                    ).values(
                        'coordination__unity_id'
                    ).distinct()[:1],
                    output_field=CharField()
                ),
                client_name=F('student_application__student__client__name'),
                client_id=F('student_application__student__client'),
            ).distinct()

        return option_answers.values(
            "id", "application_date", "student_name", "student_id", "application_student_id", "question_id", "is_objective",
            "weight", "grade", "exam_name", "exam_id", "exam_abstract", "subject_id", 
            "subject_name", "knowledge_area_id", "knowledge_area_name", "topics", "abilities", "competences", 
            "school_class_name", "school_class_id", "grade_id", "unity_name", 
            "unity_id", "client_name", "client_id")

    def get_file_answers(self, client, year, month):
        file_answers = FileAnswer.objects.annotate(
                last_examquestion_status=Subquery(
                    StatusQuestion.objects.filter(
                        exam_question__question=OuterRef('question'),
                        exam_question__exam=OuterRef('student_application__application__exam')
                    ).order_by('-created_at').values('status')[:1]
                )
            ).filter(
                Q(student_application__application__exam='56275cdc-ba85-4a2e-a9b0-ed58312faf8f'),
                Q(student_application__student__client=client),
                Q(created_at__year=year),
                Q(created_at__month=month),
                Q(
                    Q(last_examquestion_status__isnull=True) |
                    ~Q(last_examquestion_status__in=[
                        StatusQuestion.REPROVED,
                        StatusQuestion.ANNULLED
                    ])
                )
            ).annotate(
                application_date=F('student_application__application__date'),
                student_name=F('student_application__student__name'),
                student_id=F('student_application__student_id'),
                application_student_id=F('student_application'),
                is_objective=Value(False),
                weight=Subquery(
                    ExamQuestion.objects.filter(
                        exam=OuterRef('student_application__application__exam'),
                        question=OuterRef('question')
                    ).values('weight')[:1],
                    output_field=DecimalField()
                ),
                grade=Coalesce(
                    F('teacher_grade'),
                    Value(0.0),
                    output_field=DecimalField()
                ),
                exam_name=F('student_application__application__exam__name'),
                exam_id=F('student_application__application__exam_id'),
                exam_abstract=F('student_application__application__exam__is_abstract'),
                subject_id=Case(
                    When(
                        student_application__application__exam__is_abstract=False, 
                        then=Subquery(
                            ExamTeacherSubject.objects.filter(
                                exam=OuterRef('student_application__application__exam'),
                                examquestion__question=OuterRef('question')
                            ).distinct().values('teacher_subject__subject_id')[:1],
                            output_field=UUIDField()
                        ),
                    ),
                    default=F('question__subject_id')
                ),
                subject_name=Case(
                    When(
                        student_application__application__exam__is_abstract=False, 
                        then=Subquery(
                            ExamTeacherSubject.objects.filter(
                                exam=OuterRef('student_application__application__exam'),
                                examquestion__question=OuterRef('question')
                            ).distinct().values('teacher_subject__subject__name')[:1],
                            output_field=CharField()
                        ),
                    ),
                    default=F('question__subject__name')
                ),
                knowledge_area_id=Case(
                    When(
                        student_application__application__exam__is_abstract=False, 
                        then=Subquery(
                            ExamTeacherSubject.objects.filter(
                                exam=OuterRef('student_application__application__exam'),
                                examquestion__question=OuterRef('question')
                            ).distinct().values('teacher_subject__subject__knowledge_area_id')[:1],
                            output_field=UUIDField()
                        ),
                    ),
                    default=F('question__subject__knowledge_area_id')
                ),
                knowledge_area_name=Case(
                    When(
                        student_application__application__exam__is_abstract=False, 
                        then=Subquery(
                            ExamTeacherSubject.objects.filter(
                                exam=OuterRef('student_application__application__exam'),
                                examquestion__question=OuterRef('question')
                            ).distinct().values('teacher_subject__subject__knowledge_area__name')[:1],
                            output_field=CharField()
                        ),
                    ),
                    default=F('question__subject__knowledge_area__name')
                ),
                topics=ArraySubquery(
                    Topic.objects.filter(question=OuterRef('question')).values(
                        json=JSONObject(id='id', name='name')
                    ).distinct()
                ),
                abilities=ArraySubquery(
                    Abiliity.objects.filter(question=OuterRef('question')).values(
                        json=JSONObject(id='id', code='code', text='text')
                    ).distinct()
                ),
                competences=ArraySubquery(
                    Competence.objects.filter(question=OuterRef('question')).values(
                        json=JSONObject(id='id', code='code', text='text')
                    ).distinct()
                ),
                school_class_name=Subquery(
                    SchoolClass.objects.filter(
                        school_year=year,
                        students=OuterRef('student_application__student')
                    ).distinct().values(
                        'name'
                    )[:1],
                    output_field=CharField()
                ),
                school_class_id=Subquery(
                    SchoolClass.objects.filter(
                        school_year=year,
                        students=OuterRef('student_application__student')
                    ).distinct().values(
                        'id'
                    )[:1],
                    output_field=CharField()
                ),
                grade_id=Subquery(
                    SchoolClass.objects.filter(
                        school_year=year,
                        students=OuterRef('student_application__student')
                    ).distinct().values(
                        'grade_id'
                    )[:1],
                    output_field=CharField()
                ),
                unity_name=Subquery(
                    SchoolClass.objects.filter(
                        school_year=year,
                        students=OuterRef('student_application__student')
                    ).values(
                        'coordination__unity__name'
                    ).distinct()[:1],
                    output_field=CharField()
                ),
                unity_id=Subquery(
                    SchoolClass.objects.filter(
                        school_year=year,
                        students=OuterRef('student_application__student')
                    ).values(
                        'coordination__unity_id'
                    ).distinct()[:1],
                    output_field=CharField()
                ),
                client_name=F('student_application__student__client__name'),
                client_id=F('student_application__student__client'),
            ).distinct()
        
        return file_answers.values(
            "id", "application_date", "student_name", "student_id", "application_student_id", "question_id", "is_objective", 
            "weight", "grade", "exam_name", "exam_id", "exam_abstract", "subject_id", 
            "subject_name", "knowledge_area_id", "knowledge_area_name", "topics", "abilities", "competences", 
            "school_class_name", "school_class_id", "grade_id", "unity_name", 
            "unity_id", "client_name", "client_id")

    def get_textual_answers(self, client, year, month):
        textual_answers = TextualAnswer.objects.annotate(
                last_examquestion_status=Subquery(
                    StatusQuestion.objects.filter(
                        exam_question__question=OuterRef('question'),
                        exam_question__exam=OuterRef('student_application__application__exam'),
                    ).order_by('-created_at').values('status')[:1]
                )
            ).filter(
                Q(student_application__application__exam='56275cdc-ba85-4a2e-a9b0-ed58312faf8f'),
                Q(student_application__student__client=client),
                Q(created_at__year=year),
                Q(created_at__month=month),
                Q(
                    Q(last_examquestion_status__isnull=True) |
                    ~Q(last_examquestion_status__in=[
                        StatusQuestion.REPROVED,
                        StatusQuestion.ANNULLED
                    ])
            )
            ).distinct().annotate(
                application_date=F('student_application__application__date'),
                student_name=F('student_application__student__name'),
                student_id=F('student_application__student_id'),
                application_student_id=F('student_application'),
                is_objective=Value(False),
                weight=Subquery(
                    ExamQuestion.objects.filter(
                        exam=OuterRef('student_application__application__exam'),
                        question=OuterRef('question')
                    ).values('weight')[:1],
                    output_field=DecimalField()
                ),
                grade=Coalesce(
                    F('teacher_grade'),
                    Value(0.0),
                    output_field=DecimalField()
                ),
                exam_name=F('student_application__application__exam__name'),
                exam_id=F('student_application__application__exam_id'),
                exam_abstract=F('student_application__application__exam__is_abstract'),
                subject_id=Case(
                    When(
                        student_application__application__exam__is_abstract=False, 
                        then=Subquery(
                            ExamTeacherSubject.objects.filter(
                                exam=OuterRef('student_application__application__exam'),
                                examquestion__question=OuterRef('question')
                            ).distinct().values('teacher_subject__subject_id')[:1],
                            output_field=UUIDField()
                        ),
                    ),
                    default=F('question__subject_id')
                ),
                subject_name=Case(
                    When(
                        student_application__application__exam__is_abstract=False, 
                        then=Subquery(
                            ExamTeacherSubject.objects.filter(
                                exam=OuterRef('student_application__application__exam'),
                                examquestion__question=OuterRef('question')
                            ).distinct().values('teacher_subject__subject__name')[:1],
                            output_field=CharField()
                        ),
                    ),
                    default=F('question__subject__name')
                ),
                knowledge_area_id=Case(
                    When(
                        student_application__application__exam__is_abstract=False, 
                        then=Subquery(
                            ExamTeacherSubject.objects.filter(
                                exam=OuterRef('student_application__application__exam'),
                                examquestion__question=OuterRef('question')
                            ).distinct().values('teacher_subject__subject__knowledge_area_id')[:1],
                            output_field=UUIDField()
                        ),
                    ),
                    default=F('question__subject__knowledge_area_id')
                ),
                knowledge_area_name=Case(
                    When(
                        student_application__application__exam__is_abstract=False, 
                        then=Subquery(
                            ExamTeacherSubject.objects.filter(
                                exam=OuterRef('student_application__application__exam'),
                                examquestion__question=OuterRef('question')
                            ).distinct().values('teacher_subject__subject__knowledge_area__name')[:1],
                            output_field=CharField()
                        ),
                    ),
                    default=F('question__subject__knowledge_area__name')
                ),
                topics=ArraySubquery(
                    Topic.objects.filter(question=OuterRef('question')).values(
                        json=JSONObject(id='id', name='name')
                    ).distinct()
                ),
                abilities=ArraySubquery(
                    Abiliity.objects.filter(question=OuterRef('question')).values(
                        json=JSONObject(id='id', code='code', text='text')
                    ).distinct()
                ),
                competences=ArraySubquery(
                    Competence.objects.filter(question=OuterRef('question')).values(
                        json=JSONObject(id='id', code='code', text='text')
                    ).distinct()
                ),
                school_class_name=Subquery(
                    SchoolClass.objects.filter(
                        school_year=year,
                        students=OuterRef('student_application__student')
                    ).distinct().values(
                        'name'
                    )[:1],
                    output_field=CharField()
                ),
                school_class_id=Subquery(
                    SchoolClass.objects.filter(
                        school_year=year,
                        students=OuterRef('student_application__student')
                    ).distinct().values(
                        'id'
                    )[:1],
                    output_field=CharField()
                ),
                grade_id=Subquery(
                    SchoolClass.objects.filter(
                        school_year=year,
                        students=OuterRef('student_application__student')
                    ).distinct().values(
                        'grade_id'
                    )[:1],
                    output_field=CharField()
                ),
                unity_name=Subquery(
                    SchoolClass.objects.filter(
                        school_year=year,
                        students=OuterRef('student_application__student')
                    ).values(
                        'coordination__unity__name'
                    ).distinct()[:1],
                    output_field=CharField()
                ),
                unity_id=Subquery(
                    SchoolClass.objects.filter(
                        school_year=year,
                        students=OuterRef('student_application__student')
                    ).values(
                        'coordination__unity_id'
                    ).distinct()[:1],
                    output_field=CharField()
                ),
                client_name=F('student_application__student__client__name'),
                client_id=F('student_application__student__client'),
            ).distinct()

        return textual_answers.values(
            "id", "application_date", "student_name", "student_id", "application_student_id", "question_id", "is_objective", 
            "weight", "grade", "exam_name", "exam_id", "exam_abstract", "subject_id", 
            "subject_name", "knowledge_area_id", "knowledge_area_name", "topics", "abilities", "competences", 
            "school_class_name", "school_class_id", "grade_id", "unity_name", 
            "unity_id", "client_name", "client_id")

    def handle(self, *args, **kwargs):
        year = (kwargs.get('year', None) or [timezone.now().year])[0]
        month = (kwargs.get('month', None) or [timezone.now().month])[0]

        print(f'Processo iniciado [{timezone.now()}]')

        clients = Client.objects.filter(
            # status__in=[
            #     Client.ACTIVED,
            #     Client.IN_POC
            # ],
            pk__in=[
                # '47073c60-c3a8-4b8b-9319-d72c3e8165f9', #NR
                # 'a2b1158b-367a-40a4-8413-9897057c8aa2'  #Desisão
                '86ba20fe-3822-4f72-ab9a-01720bf93662'  #PH
                # '7157df0b-f3d2-4374-af2b-a9b169c728bf'  #Xandão
            ]
        )

        tmp_directory = os.path.join('tmp', 'parquet')
        os.makedirs(tmp_directory, exist_ok=True)

        base_remote_name = f'parquet/performance/base.parq'

        if kwargs.get('schema', False):
            base_schema_filename = self._create_base_schema_parquet(tmp_directory)
            storage_service.upload_file(base_schema_filename, base_remote_name)
            return

        for client in clients:
            print(f'Processando respostas de {client.name} ({year})')

            if not kwargs.get('dryrun', False):
                print("Recriando dataset no Bigquery...")
                bigquery_service.load_from_parquet(
                    base_remote_name,
                    f'fiscallize.performance.answers_{client.pk}_{year}'
                )

            for m in range(1, month + 1):
                print(f'- Mês: {m}')
                option_answers = self.get_option_answers(client, year, m)

                if option_answers:
                    option_answers_filename = os.path.join(tmp_directory, f'{client.pk}_optionanswers_{m}_{year}.parquet')
                    self._save_qs_to_parquet(option_answers, option_answers_filename)
                    print(f'  {option_answers.count()} option_answers processadas')

                    if not kwargs.get('dryrun', False):
                        remote_name = f'parquet/performance/optionanswers_{client.pk}_{m}_{year}.parq'
                        storage_service.upload_file(option_answers_filename, remote_name)
                        bigquery_service.load_from_parquet(
                            remote_name,
                            f'fiscallize.performance.answers_{client.pk}_{year}',
                            append=True,
                        )
                        os.remove(option_answers_filename)

                file_answers = self.get_file_answers(client, year, m)
                if file_answers:
                    file_answers_filename = os.path.join(tmp_directory, f'{client.pk}_fileanswers_{m}_{year}.parquet')
                    self._save_qs_to_parquet(file_answers, file_answers_filename)
                    print(f'  {file_answers.count()} file_answers processadas')

                    if not kwargs.get('dryrun', False):
                        remote_name = f'parquet/performance/fileanswers_{client.pk}_{m}_{year}.parq'
                        storage_service.upload_file(file_answers_filename, remote_name)
                        bigquery_service.load_from_parquet(
                            remote_name,
                            f'fiscallize.performance.answers_{client.pk}_{year}',
                            append=True,
                        )
                        os.remove(file_answers_filename)

                textual_answers = self.get_textual_answers(client, year, m)
                if textual_answers:
                    textual_answers_filename = os.path.join(tmp_directory, f'{client.pk}_textualanswers_{m}_{year}.parquet')
                    self._save_qs_to_parquet(textual_answers, textual_answers_filename)
                    print(f'  {textual_answers.count()} textual_answers processadas')

                    if not kwargs.get('dryrun', False):
                        remote_name = f'parquet/performance/textualanswers_{client.pk}_{m}_{year}.parq'
                        storage_service.upload_file(textual_answers_filename, remote_name)
                        bigquery_service.load_from_parquet(
                            remote_name,
                            f'fiscallize.performance.answers_{client.pk}_{year}',
                            append=True,
                        )
                        os.remove(textual_answers_filename)

        print(f'Processo finalizado [{timezone.now()}]')

