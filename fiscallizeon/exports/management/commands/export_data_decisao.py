import os
import shutil
import glob
from datetime import datetime

from decouple import config
import boto3
import pandas as pd
from fastparquet import write

from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models.functions import Cast, Coalesce, Concat
from django.db.models import CharField, F, Q, Subquery, OuterRef, Case, When, Value, DecimalField
from django.core.management.base import BaseCommand

from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.students.models import Student
from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.subjects.models import Subject, Topic
from fiscallizeon.clients.models import Client, SchoolCoordination, Unity
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.questions.models import Question, BaseText
from fiscallizeon.bncc.models import Abiliity, Competence
from fiscallizeon.exams.models import Exam, ExamQuestion, ExamTeacherSubject, StatusQuestion
from fiscallizeon.answers.models import FileAnswer, TextualAnswer, OptionAnswer

class Command(BaseCommand):
    help = 'Exporta dados para formato parquet da Rede decisão (comprimidos em GZIP)'
    #DOCS: https://glittery-profit-ea1.notion.site/Exporta-o-dados-parquet-9d0c399bc226426a946b66eee887a7ee

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.today = datetime.now()

        self.base_tmp_dir = os.path.join(
            os.sep, 'code', 'tmp', 'export', 'parquet', self.today.strftime('%Y-%m-%d')
        )
        os.makedirs(self.base_tmp_dir, exist_ok=True)

    def upload_to_bucket(self):
        today_str = self.today.strftime('%Y-%m-%d')

        s3 = boto3.resource(
            's3', 
            aws_access_key_id=config('DECISAO_AWS_ACCESS_KEY_ID'), 
            aws_secret_access_key=config('DECISAO_AWS_SECRET_ACCESS_KEY')
        )

        files = glob.glob(os.path.join(self.base_tmp_dir, '*.parq'))
        for parquet_file in files:
            print(parquet_file)
            # Filename - File to upload
            # Bucket - Bucket to upload to (the top level directory under AWS S3)
            # Key - S3 object name (can contain subdirectories). If not specified then file_name is used
            s3.meta.client.upload_file(
                Filename=parquet_file,
                Bucket='fiscalize-csv',
                Key=f'exportacoes-parquet/{today_str}/{os.path.basename(parquet_file)}'
            )

        #Apagar diretório base
        shutil.rmtree(self.base_tmp_dir)

    def handle(self, *args, **kwargs):
        print("### Iniciando exportação")
        client = Client.objects.get(pk='a2b1158b-367a-40a4-8413-9897057c8aa2') #Decisão

        print("- Exportando dados de alunos")
        students = Student.objects.filter(
            client=client
        ).annotate(
            school_classes=ArrayAgg(Cast('classes', output_field=CharField()))
        ).values()

        df = pd.DataFrame.from_records(students, columns=[
            'id', 'name', 'enrollment_number', 'email', 'school_classes'
        ])
        df = df.astype({"id": str})
        final_filename = os.path.join(self.base_tmp_dir, 'alunos.parq')
        write(final_filename, df, compression='GZIP')

        print("- Exportando dados de turmas")
        school_classes = SchoolClass.objects.filter(
            coordination__unity__client=client,
            school_year=self.today.year
        ).annotate(
            coordination_uuid=Cast('coordination_id', CharField()),
            grade_name=Case(
                When(grade__level=0, then=Concat(Value('Ensino médio - '), F('grade__name'), Value('ª série'))),
                When(grade__level=1, then=Concat(Value('Ensino fundamental - '), F('grade__name'), Value('º ano'))),
                default=Value('Indefinido'),
            )
        ).values()

        df = pd.DataFrame.from_records(school_classes, columns=[
            'id', 'name', 'coordination_uuid', 'grade_name', 'school_year', 'temporary_class',
        ])
        df = df.astype({'id': str})
        final_filename = os.path.join(self.base_tmp_dir, 'turmas.parq')
        write(final_filename, df, compression='GZIP')

        print("- Exportando dados de coordenações")
        coordinations = SchoolCoordination.objects.filter(
            unity__client=client,
        ).annotate(
            unity_uuid=Cast('unity', output_field=CharField())
        ).values()

        df = pd.DataFrame.from_records(coordinations, columns=[
            'id', 'name', 'unity_uuid'
        ])
        df = df.astype({'id': str})
        final_filename = os.path.join(self.base_tmp_dir, 'coordenacoes.parq')
        write(final_filename, df, compression='GZIP')

        print("- Exportando dados de unidades")
        unities = Unity.objects.filter(
            client=client,
        ).values()

        df = pd.DataFrame.from_records(unities, columns=[
            'id', 'name'
        ])
        df = df.astype({'id': str})
        final_filename = os.path.join(self.base_tmp_dir, 'unidades.parq')
        write(final_filename, df, compression='GZIP')

        print("- Exportando dados de disciplinas")
        subjects = Subject.objects.filter(
            Q(client=client)
        ).annotate(
            knowledge_area_description=F('knowledge_area__name')
        ).values()

        df = pd.DataFrame.from_records(subjects, columns=[
            'id', 'name', 'knowledge_area_description',
        ])
        df = df.astype({'id': str})
        final_filename = os.path.join(self.base_tmp_dir, 'disciplinas.parq')
        write(final_filename, df, compression='GZIP')

        print("- Exportando dados de professores")
        inspectors = Inspector.objects.filter(
            coordinations__unity__client=client
        ).annotate(
            coordinations_list=ArrayAgg(Cast('coordinations', output_field=CharField()), distinct=True),
            subjects_list=ArrayAgg(Cast('subjects', output_field=CharField()), distinct=True),
            classes_list=ArrayAgg(Cast('classes_he_teaches', output_field=CharField()), distinct=True),
        ).distinct().values()

        df = pd.DataFrame.from_records(inspectors, columns=[
            'id', 'name', 'email', 'coordinations_list', 'subjects_list', 'classes_list',
        ])
        df = df.astype({'id': str})
        final_filename = os.path.join(self.base_tmp_dir, 'professores.parq')
        write(final_filename, df, compression='GZIP')

        print("- Exportando dados de BNCC: habilidades")
        abiliities = Abiliity.objects.filter(
            Q(client=client) |
            Q(client__isnull=True)
        ).values()

        df = pd.DataFrame.from_records(abiliities, columns=[
            'id', 'code', 'text'
        ])
        df = df.astype({'id': str})
        final_filename = os.path.join(self.base_tmp_dir, 'habilidades_bncc.parq')
        write(final_filename, df, compression='GZIP')

        print("- Exportando dados de BNCC: competências")
        competences = Competence.objects.filter(
            Q(client=client) |
            Q(client__isnull=True)
        ).values()

        df = pd.DataFrame.from_records(competences, columns=[
            'id', 'code', 'text'
        ])
        df = df.astype({'id': str})
        final_filename = os.path.join(self.base_tmp_dir, 'competencias_bncc.parq')
        write(final_filename, df, compression='GZIP')

        print("- Exportando textos base")
        base_texts = BaseText.objects.filter(
            question__coordinations__unity__client=client,
        ).annotate(
            creator=F('created_by__name')
        ).distinct().values()

        df = pd.DataFrame.from_records(base_texts, columns=[
            'id', 'title', 'text', 'creator'
        ])
        df = df.astype({'id': str})
        final_filename = os.path.join(self.base_tmp_dir, 'textos_base.parq')
        write(final_filename, df, compression='GZIP')

        print("- Exportando assuntos")
        topics = Topic.objects.filter(
            question__coordinations__unity__client=client,
        ).annotate(
            creator=F('created_by'),
            subject_uuid=Cast('subject_id', CharField()),
            stage_description=Case(
                When(stage=1, then=Value('1ª etapa')),
                When(stage=2, then=Value('2ª etapa')),
                When(stage=3, then=Value('3ª etapa')),
                When(stage=4, then=Value('4ª etapa')),
                When(stage=5, then=Value('5ª etapa')),
                When(stage=6, then=Value('6ª etapa')),
                default=Value('Geral')
            ),
            grade_name=Case(
                When(grade__level=0, then=Concat(Value('Ensino médio - '), F('grade__name'), Value('ª série'))),
                When(grade__level=1, then=Concat(Value('Ensino fundamental - '), F('grade__name'), Value('º ano'))),
                default=Value('Indefinido'),
            ),
        ).distinct().values()

        df = pd.DataFrame.from_records(topics, columns=[
            'id', 'name', 'subject_uuid', 'creator', 'stage_description', 'grade_name',
        ])
        df = df.astype({'id': str, 'subject_uuid': str})
        final_filename = os.path.join(self.base_tmp_dir, 'topicos.parq')
        write(final_filename, df, compression='GZIP')

        print("- Exportando dados de questões")
        questions = Question.objects.filter(
            coordinations__unity__client=client,
            is_abstract=False,
        ).annotate(
            alternatives_list=ArrayAgg(Cast('alternatives__text', output_field=CharField())),
            topics_list=ArrayAgg(Cast('topics__name', output_field=CharField()), distinct=True, default=[]),
            abilities_list=ArrayAgg(Cast('abilities__pk', output_field=CharField()), distinct=True, default=[]),
            competences_list=ArrayAgg(Cast('competences__pk', output_field=CharField()), distinct=True, default=[]),
            base_texts_list=ArrayAgg(Cast('base_texts__pk', output_field=CharField()), distinct=True, default=[]),
            creator=F('created_by__name'),
            level_description=Case(
                When(level=0, then=Value('Fácil')),
                When(level=1, then=Value('Médio')),
                When(level=2, then=Value('Difícil')),
                default=Value('Indefinido')
            ),
            category_description=Case(
                When(category=0, then=Value('Discursiva')),
                When(category=1, then=Value('Objetiva')),
                When(category=2, then=Value('Arquivo anexado')),
                default=Value('Indefinido')
            )
        ).distinct().values()

        df = pd.DataFrame.from_records(questions, columns=[
            'id', 'level_description', 'enunciation', 'category_description', 'commented_awnser', 'feedback', 
            'alternatives_list', 'creator', 'topics_list', 'subject_id', 'abilities_list',
            'competences_list', 'adapted', 'base_texts_list',
        ])
        df = df.astype({'id': str, 'subject_id': str})
        final_filename = os.path.join(self.base_tmp_dir, 'questoes.parq')
        write(final_filename, df, compression='GZIP')

        print("- Exportando dados de cadernos")
        exams = Exam.objects.filter(
            coordinations__unity__client=client,
            is_abstract=False,
        ).annotate_total_weight().annotate(
            creator=F('created_by__name'),
            status_description=Case(
                When(status=0, then=Value('Elaborando')),
                When(status=1, then=Value('Revisão de itens')),
                When(status=2, then=Value('Fechada')),
                When(status=3, then=Value('Diagramação')),
                default=Value('Não informado')
            ),
            category_description=Case(
                When(status=0, then=Value('Prova')),
                When(status=1, then=Value('Lista de Exercício')),
                default=Value('Não informado')
            )
        ).distinct().values()

        df = pd.DataFrame.from_records(exams, columns=[
            'id', 'name', 'status_description', 'random_alternatives', 'random_questions', 'is_english_spanish', 'category_description',
            'correction_by_subject', 'elaboration_deadline', 'creator', 'release_elaboration_teacher', 'show_ranking', 'total_weight'
        ])
        df = df.astype({'id': str, 'elaboration_deadline': str, 'release_elaboration_teacher': str})
        final_filename = os.path.join(self.base_tmp_dir, 'cadernos.parq')
        write(final_filename, df, compression='GZIP')

        print("- Exportando dados de solicitações")
        exam_teacher_subject = ExamTeacherSubject.objects.filter(
            exam__in=exams.values('pk'),
        ).annotate(
            teacher_id=F('teacher_subject__teacher'),
            subject_id=F('teacher_subject__subject')
        ).distinct().values()

        df = pd.DataFrame.from_records(exam_teacher_subject, columns=[
            'id', 'teacher_id', 'subject_id', 'exam_id', 'quantity', 'note', 'teacher_note',
        ])
        df = df.astype({'id': str, 'teacher_id': str, 'subject_id': str, 'exam_id': str})
        final_filename = os.path.join(self.base_tmp_dir, 'solicitacoes.parq')
        write(final_filename, df, compression='GZIP')
        
        print("- Exportando questões dos cadernos")
        exam_questions = ExamQuestion.objects.filter(
            exam__in=exams.values('pk')
        ).annotate(
            request_id=F('exam_teacher_subject_id'),
            status=Coalesce(
                Subquery(
                    StatusQuestion.objects.filter(
                        exam_question=OuterRef('pk')
                    ).order_by('-created_at').values('status')[:1]
                ), 2),
            status_description=Case(
                When(status=0, then=Value('Aprovada')),
                When(status=1, then=Value('Reprovada')),
                When(status=3, then=Value('Aguardando correção')),
                When(status=4, then=Value('Corrigido')),
                When(status=5, then=Value('Visto')),
                default=Value('Em aberto')
            )
            
        ).values()

        df = pd.DataFrame.from_records(exam_questions, columns=[
            'id', 'question_id', 'exam_id', 'request_id', 'order', 'weight', 'status_description',
        ])
        df = df.astype({'id': str, 'question_id': str, 'exam_id': str, 'request_id': str})
        final_filename = os.path.join(self.base_tmp_dir, 'questoes_cadernos.parq')
        write(final_filename, df, compression='GZIP')

        print('- Exportando dados de respostas')
        option_answers = OptionAnswer.objects.filter(
            student_application__student__client=client,
        ).annotate(
            content=F('question_option__text'),
            student_id=F('student_application__student'),
            exam_question=Subquery(
                ExamQuestion.objects.filter(
                    exam=OuterRef('student_application__application__exam'),
                    question=OuterRef('question_option__question')
                ).values('pk')[:1]
            ),
            weight=Subquery(
                ExamQuestion.objects.filter(
                    exam=OuterRef('student_application__application__exam'),
                    question=OuterRef('question_option__question')
                ).values('weight')[:1]
            ),
            grade=Case(
                When(question_option__is_correct=True, then=F('weight')),
                default=Value(0, output_field=DecimalField())
            ),
            category=Value('choice')
        ).values('id', 'exam_question', 'content', 'student_id', 'weight', 'grade', 'category')

        textual_answers = TextualAnswer.objects.filter(
            student_application__student__client=client,
        ).annotate(
            student_id=F('student_application__student'),
            exam_question=Subquery(
                ExamQuestion.objects.filter(
                    exam=OuterRef('student_application__application__exam'),
                    question=OuterRef('question')
                ).values('pk')[:1]
            ),
            weight=Subquery(
                ExamQuestion.objects.filter(
                    exam=OuterRef('student_application__application__exam'),
                    question=OuterRef('question')
                ).values('weight')[:1]
            ),
            grade=F('teacher_grade'),
            category=Value('textual'),
        ).values('id', 'exam_question', 'content', 'student_id', 'weight', 'grade', 'category')

        file_answers = FileAnswer.objects.filter(
            student_application__student__client=client,
        ).annotate(
            content=F('arquivo'),
            student_id=F('student_application__student'),
            exam_question=Subquery(
                ExamQuestion.objects.filter(
                    exam=OuterRef('student_application__application__exam'),
                    question=OuterRef('question')
                ).values('pk')[:1]
            ),
            weight=Subquery(
                ExamQuestion.objects.filter(
                    exam=OuterRef('student_application__application__exam'),
                    question=OuterRef('question')
                ).values('weight')[:1]
            ),
            grade=F('teacher_grade'),
            category=Value('file'),
        ).values('id', 'exam_question', 'content', 'student_id', 'weight', 'grade', 'category')

        answers = option_answers.union(textual_answers).union(file_answers)
        df = pd.DataFrame.from_records(answers, columns=[
            'id', 'exam_question', 'content', 'student_id', 'weight', 'grade', 'category'
        ])
        df = df.astype({'id': str, 'exam_question': str, 'student_id': str})
        final_filename = os.path.join(self.base_tmp_dir, 'respostas.parq')
        write(final_filename, df, compression='GZIP')

        print("- Exportando resultados")
        applicaton_students = ApplicationStudent.objects.filter(
            Q(student__client=client) &
            Q(
                Q(option_answers__isnull=False) |
                Q(file_answers__isnull=False) |
                Q(textual_answers__isnull=False)
            )
        ).get_annotation_count_answers(
            only_total_grade=True,
        ).annotate(
            exam=F('application__exam__name'),
            exam_id=F('application__exam_id'),
            enrollment=F('student__enrollment_number'),
            grade=F('total_grade'),
        ).values()

        df = pd.DataFrame.from_records(applicaton_students, columns=[
            'student_id', 'enrollment', 'exam_id', 'exam', 'grade'
        ])
        df = df.astype({'student_id': str, 'exam_id': str})
        final_filename = os.path.join(self.base_tmp_dir, 'resultados.parq')
        write(final_filename, df, compression='GZIP')

        print("- Exportando aplicações")
        applications = Application.objects.filter(
            students__client=client,
        ).annotate(
            classes_ids=ArrayAgg(Cast('school_classes', output_field=CharField())),
            students_ids=ArrayAgg(Cast('students', output_field=CharField())),
            finish_date=Cast('date_end', output_field=CharField()),
            start_date=Cast('date', output_field=CharField()),
            start_time=Cast('start', output_field=CharField()),
            finish_time=Cast('end', output_field=CharField()),
            category_description=Case(
                When(category=2, then=Value('Online')),
                When(category=3, then=Value('Presencial')),
                When(category=4, then=Value('Lista de Exercício')),
                default=Value('Indefinido')
            )
        ).values()

        df = pd.DataFrame.from_records(applications, columns=[
            'id', 'classes_ids', 'students_ids', 'exam_id', 'start_date', 'start_time', 'finish_time', 'finish_date', 'category_description'
        ])
        df = df.astype({'id': str, 'exam_id': str})
        final_filename = os.path.join(self.base_tmp_dir, 'aplicacoes.parq')
        write(final_filename, df, compression='GZIP')

        print("### Iniciando upload para S3")
        self.upload_to_bucket()
        print("### Exportação concluída")