import os
import glob

import numpy as np
import pyarrow as pa
import pandas as pd
import pyarrow.parquet as pq

from django.utils import timezone
from django.core.management.base import BaseCommand
from django.db.models import F, Case, When

from fiscallizeon.classes.models import Client
from fiscallizeon.questions.models import Question
from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.core.gcp import storage_service
from fiscallizeon.core.gcp import bigquery_service

class Command(BaseCommand):
    help = 'Exporta todas as ExamQuestion de um ano para o o Google Bigquery'

    def add_arguments(self, parser):
        parser.add_argument('--year', nargs=1, type=int, required=False)
        parser.add_argument('--dryrun', action='store_true', default=False, help='Executa sem subir arquivos para GCP')
        parser.add_argument('--schema', action='store_true', default=False, help='Apenas cria arquivo parquet com schema no GCS')

    def _get_pyarrow_schema(self):
        return pa.schema([
            ('id', pa.string()),
            ('question_id', pa.string()),
            ('exam_id', pa.string()),
            ('weight', pa.float64()),
            ('order', pa.int8()),
            ('subject_order', pa.int8()),
            ('is_objective', pa.bool_()),
            ('is_foreign', pa.bool_()),
            ('subject_id', pa.string()),
            ('subject_name', pa.string()),
            ('knowledge_area_id', pa.string()),
        ])

    def _save_qs_to_parquet(self, queryset, filename, empty=False):
        df = pd.json_normalize(list(queryset))
        df = df.astype({"id": str})
        df = df.astype({"question_id": str})
        df = df.astype({"exam_id": str})
        df = df.astype({"subject_id": str})
        df = df.astype({"knowledge_area_id": str})
        df = df.astype({"weight": float})

        df['subject_id'] = df['subject_id'].replace('None', '0')
        df['knowledge_area_id'] = df['knowledge_area_id'].replace('None', '0')

        if empty:
            df = df.drop(df.index)

        schema = self._get_pyarrow_schema()
        table = pa.Table.from_pandas(df, schema=schema, preserve_index=True)
        pq.write_table(table, filename, compression='gzip')

    def _create_base_schema_parquet(self, tmp_directory):
        print('Criando parquet schema para bigquery...')
        client = Client.objects.get(pk='a2b1158b-367a-40a4-8413-9897057c8aa2')
        exam_questions = self.get_exam_questions(client, 2022)
        base_schema_filename = os.path.join(tmp_directory, f'base_examquestions.parquet')
        self._save_qs_to_parquet(exam_questions, base_schema_filename, empty=True)
        return base_schema_filename

    def get_exam_questions(self, client, year):
        exam_questions = ExamQuestion.objects.filter(
            exam__coordinations__unity__client=client,
            created_at__year=year,
        ).annotate(
            subject_order=F('exam_teacher_subject__order'),
            is_abstract_exam=F('is_abstract'),
            is_objective=Case(
                When(question__category=Question.CHOICE, then=True),
                default=False
            ),
            is_foreign=Case(
                When(exam__is_abstract=False, then=F('exam_teacher_subject__is_foreign_language')),
                When(exam__is_abstract=True, then=F('is_foreign_language')),
            ),
            subject_id=Case(
                When(
                    exam__is_abstract=False, 
                    then=F('exam_teacher_subject__teacher_subject__subject_id')
                ),
                default=F('question__subject_id')
            ),
            subject_name=Case(
                When(
                    exam__is_abstract=False, 
                    then=F('exam_teacher_subject__teacher_subject__subject__name')
                ),
                default=F('question__subject__name')
            ),
            knowledge_area_id=Case(
                When(
                    exam__is_abstract=False, 
                    then=F('exam_teacher_subject__teacher_subject__subject__knowledge_area_id')
                ),
                default=F('question__subject__knowledge_area_id')
            ),
        ).distinct()

        return exam_questions.values(
            "id", "question_id", "exam_id", "weight", "order",
            "subject_order", "is_foreign", "is_abstract_exam", 
            "is_objective", "subject_id", "subject_name", 
            "knowledge_area_id"
        )


    def handle(self, *args, **kwargs):
        year = (kwargs.get('year', None) or [timezone.now().year])[0]

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

        tmp_directory = os.path.join('tmp', 'examquestions-parquet')
        os.makedirs(tmp_directory, exist_ok=True)

        base_remote_name = f'parquet/performance/base-examquestions.parq'

        if kwargs.get('schema', False):
            base_schema_filename = self._create_base_schema_parquet(tmp_directory)
            storage_service.upload_file(base_schema_filename, base_remote_name)
            return

        for client in clients:
            print(f'Processando questões de {client.name} ({year})')

            exam_questions = self.get_exam_questions(client, year)
            if not exam_questions:
                continue

            exam_questions_filename = os.path.join(tmp_directory, f'{client.pk}_examquestions_{year}.parquet')
            self._save_qs_to_parquet(exam_questions, exam_questions_filename)
            print(f'{exam_questions.count()} exam_questions processadas')

            if not kwargs.get('dryrun', False):
                print("Recriando dataset no Bigquery...")
                bigquery_service.load_from_parquet(
                    base_remote_name,
                    f'fiscallize.performance.examquestions_{client.pk}_{year}'
                )

                remote_name = f'parquet/performance/{client.pk}_examquestions_{year}.parq'
                storage_service.upload_file(exam_questions_filename, remote_name)
                bigquery_service.load_from_parquet(
                    remote_name,
                    f'fiscallize.performance.examquestions_{client.pk}_{year}',
                    append=True,
                )
        
        for parquet_file in glob.glob(f'{tmp_directory}/*.parq'):
            os.remove(parquet_file)

        print(f'Processo finalizado [{timezone.now()}]')

