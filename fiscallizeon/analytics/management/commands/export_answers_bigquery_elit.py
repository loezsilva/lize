import os

import pyarrow as pa
import pandas as pd
import pyarrow.parquet as pq

from django.utils import timezone
from django.core.management.base import BaseCommand
from django.db.models.functions import Coalesce
from django.db.models import F, Q, Subquery, OuterRef, Case, When, Value, DecimalField, CharField

from fiscallizeon.classes.models import Client
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.answers.models import OptionAnswer, FileAnswer, TextualAnswer
from fiscallizeon.exams.models import ExamQuestion, StatusQuestion
from fiscallizeon.core.gcp import storage_service
from fiscallizeon.core.gcp import bigquery_service

class Command(BaseCommand):
    help = 'Exporta todas as respostas da ELIT para o bigquery'

    def _save_qs_to_parquet(self, queryset, filename):
        df = pd.json_normalize(list(queryset))
        df = df.astype({"id": str})
        df = df.astype({"weight": float})
        df = df.astype({"grade": float})
        df['grade_name'] = df['grade_name'].astype(str) + ' ano'
        df['school_class_name'] = df['school_class_name'] + ' - ' + df['unity_name']
        df['question_order'] = df['question_order'] + 1
        df['question_order'] = 'Questão ' + df['question_order'].astype(str)

        schema = pa.schema([
            ('id', pa.string()),
            ('student_name', pa.string()),
            ('weight', pa.float64()),
            ('grade', pa.float64()),
            ('question_order', pa.string()),
            ('exam_name', pa.string()),
            ('school_class_name', pa.string()),
            ('grade_name', pa.string()),
            ('unity_name', pa.string()),
        ])

        table = pa.Table.from_pandas(df, schema=schema, preserve_index=True)
        pq.write_table(table, filename, compression='gzip')

    def get_textual_answers(self, client, year):
        textual_answers = TextualAnswer.objects.filter(
            Q(student_application__application__exam__name__icontains='ELIT -'),
            Q(student_application__student__client=client),
            Q(created_at__year=year),
            Q(
                Q(question__examquestion__statusquestion__isnull=True) |
                Q(
                    Q(question__examquestion__statusquestion__active=True), 
                    ~Q(question__examquestion__statusquestion__status__in=[
                        StatusQuestion.REPROVED, 
                        StatusQuestion.ANNULLED
                    ])
                )
            )
        ).distinct().annotate(
            student_name=F('student_application__student__name'),
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
            question_order=Subquery(
                ExamQuestion.objects.filter(
                    Q(exam=OuterRef('student_application__application__exam')),
                    Q(question=OuterRef('question')),
                ).values(
                    'order'
                )[:1]
            ),
            exam_name=F('student_application__application__exam__name'),
            school_class_name=Subquery(
                SchoolClass.objects.filter(
                    school_year=year,
                    students=OuterRef('student_application__student')
                ).distinct().values(
                    'name'
                )[:1],
                output_field=CharField()
            ),
            grade_name=Subquery(
                SchoolClass.objects.filter(
                    school_year=year,
                    students=OuterRef('student_application__student')
                ).distinct().values(
                    'grade__name'
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
            client_name=F('student_application__student__client__name'),
        ).distinct()

        return textual_answers.values(
            "id", "student_name", "weight", "grade",
            "question_order", "exam_name", "school_class_name",
            "grade_name", "unity_name", "client_name")

    def handle(self, *args, **kwargs):
        year = timezone.now().year

        clients = Client.objects.filter(
            pk="5bbe72b2-7a16-4f8c-969f-554a67719c87"
        )

        tmp_directory = os.path.join('tmp', 'parquet')
        os.makedirs(tmp_directory, exist_ok=True)

        for client in clients:
            print(f'Processando respostas de {client.name}')

            textual_answers = self.get_textual_answers(client, year)
            if textual_answers:
                textual_answers_filename = os.path.join(tmp_directory, f'{client.pk}_textualanswers.parquet')
                self._save_qs_to_parquet(textual_answers, textual_answers_filename)
                print(f'- {textual_answers.count()} textual_answers processadas')
            
                remote_name = f'parquet/elit/answers_{client.pk}_{year}.parq'
                storage_service.upload_file(textual_answers_filename, remote_name)
                print("Arquivo parquet enviado para o google cloud storage")

                bigquery_service.load_from_parquet(
                    remote_name,
                    f'fiscallize.elit.answers_{client.pk}_{year}'
                )
                print("Dataset criado/atualizado no Bigquery")

                os.remove(textual_answers_filename)
                print("Arquivos parquet locais removidos")
