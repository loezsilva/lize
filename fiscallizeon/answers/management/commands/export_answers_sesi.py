import pandas as pd

from django.core.management.base import BaseCommand
from django.db.models import Subquery, OuterRef, F

from fiscallizeon.answers.models import OptionAnswer
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.exams.models import ExamQuestion


class Command(BaseCommand):
    help = 'Exporta planilha com respostas para o SESI-SP'

    def handle(self, *args, **kwargs):
        option_answers = OptionAnswer.objects.filter(
            student_application__student__client='c3d45804-f6ff-4865-a755-d41b4a79d32e',
            status=OptionAnswer.ACTIVE
        ).annotate(
            student_name=F('student_application__student__name'),
            student_enrollment=F('student_application__student__enrollment_number'),
            exam_name=F('student_application__application__exam__name'),
            index=F('question_option__index'),
            question_order=Subquery(
                ExamQuestion.objects.filter(question=OuterRef('question_option__question')).values('order')[:1]
            ),
            unity_name=Subquery(
                SchoolClass.objects.filter(
                    pk__in=OuterRef('student_application__student__classes'), 
                    school_year=2024
                ).order_by('-created_at').distinct().values('coordination__unity__name')[:1]
            ),
            coordination_name=Subquery(
                SchoolClass.objects.filter(
                    pk__in=OuterRef('student_application__student__classes'), 
                    school_year=2024
                ).order_by('-created_at').distinct().values('coordination__name')[:1]
            ),
        ).values(
            'created_at',
            'exam_name',
            'unity_name',
            'coordination_name',
            'student_name',
            'student_enrollment',
            'question_order',
            'index',
        )

        df = pd.DataFrame(option_answers)
        df['grade_name'] = df['exam_name'].str[-6]
        df = df.sort_values('created_at')
        df = df.drop_duplicates(subset=['student_name', 'student_enrollment', 'question_order', 'exam_name'], keep='last')
        df['question_order'] = 'questao_' + df['question_order'].astype(str)
        df['index'] = df['index'].replace({1: 'A', 2: 'B', 3: 'C', 4: 'D', 5: 'E'})

        df_pivot = df.pivot(
            index=['student_name', 'student_enrollment', 'grade_name', 'exam_name', 'unity_name', 'coordination_name'], 
            columns=['question_order'], 
            values='index'
        )

        columns = [
            'questao_1', 'questao_2', 'questao_3', 'questao_4', 
            'questao_5', 'questao_6', 'questao_7', 'questao_8', 
            'questao_9', 'questao_10', 'questao_11', 'questao_12', 
            'questao_13', 'questao_14', 'questao_15', 'questao_16', 
            'questao_17', 'questao_18'
        ]

        df_pivot = df_pivot[columns]
        df_pivot.to_csv('tmp/sesi.csv')
