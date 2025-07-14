import pandas as pd
import polars as pl
from django.db import connection
from django.conf import settings

from decouple import config
from decimal import Decimal
 
from django.db.models.functions import Coalesce, Concat
from django.db.models import Q, Case, Value, When, BooleanField, Subquery, OuterRef, Sum, DecimalField

from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.exams.models import Exam, ExamQuestion
from fiscallizeon.applications.models import ApplicationStudent


exams_pks = list(Exam.objects.filter(
        Q(name__icontains="2023"),
        Q(coordinations__unity__client__name__icontains="decis"),
        Q(
            Q(name__icontains="p1") #|
            # Q(name__icontains="p2") |
            # Q(name__icontains="p3") |
            # Q(name__icontains="p4") |
            # Q(name__icontains="p5") |
            # Q(name__icontains="p6")
        )
    ).exclude(
        Q(name__icontains="quest") |
        Q(name__icontains="psub") |
        Q(name__icontains="cópia") |
        Q(name__icontains="BOLSA") |
        Q(name__icontains="PREPARA") |
        Q(name__istartswith="OE")
    ).distinct().order_by('name').values_list('pk', flat=True)
)
exams = Exam.objects.filter(pk__in=exams_pks)
students = ApplicationStudent.objects.filter(
    Q(application__exam__in=exams)
).get_last_school_class()
queryset = (
        students
        # .annotate(
        #     has_answer=Case(
        #         When(
        #             Q(textual_answers__isnull=False)
        #             | Q(file_answers__isnull=False)
        #             | Q(option_answers__isnull=False)
        #             | Q(sum_answers__isnull=False),
        #             then=Value(True),
        #         ),
        #         default=Value(False),
        #         output_field=BooleanField(),
        #     )
        # )
        .annotate(
            exam_grade=Coalesce(
                Subquery(
                    ExamQuestion.objects.filter(
                        exam=OuterRef('application__exam')
                    ).availables(exclude_annuleds=True).values(
                        'exam'
                    ).annotate(
                        Sum('weight')
                    ).values('weight__sum')[:1]
                ),
                Decimal('0')
            )
        )
        .annotate(
            class_grade=Subquery(
                SchoolClass.objects.filter(
                    pk=OuterRef('school_class'),
                ).values('grade__pk')[:1]
            )
        )
        # .filter(has_answer=True)
        .get_annotation_count_answers(
            only_total_grade=True,
            exclude_annuleds=True,
        )
        .values(
            'id',
            'application__date',
            'application__exam__name',
            'exam_grade',
            'student__name',
            'total_grade',
            'class_grade',
            'missed'
        )
    )
# query = queryset.query
# sql_query, params = query.sql_with_params()
# with connection.cursor() as cursor:
#     formatted_sql_query = cursor.mogrify(sql_query, params).decode('utf-8')
# df = pl.read_database_uri(query=formatted_sql_query, uri=config('DATABASE_URL_READONLY2')).rename({ 
#     'student__name':'student_name',
#     'application__exam__name': 'exam_name'
# }).select(
#     'id',
#     'application__date',
#     'exam_name',
#     'exam_grade',
#     'student_name',
#     'total_grade',
#     'class_grade',
#     'missed'
# )

df = pd.DataFrame.from_records(queryset)
df.to_csv('tmp/notas_decisao_nota_3.csv', mode='w')


df = pd.read_csv('tmp/notas_decisao.csv')
filtro = df['application__exam__name'].str.contains('M1') & df['application__exam__examteachersubject__teacher_subject__subject__name'].str.contains('Matemática') & df['application__exam__name'].str.contains('P2')

provas_matematica_m1 = df[filtro]   
media_notas = provas_matematica_m1['total_grade'].mean()
print(media_notas)




df['application__exam__examteachersubject__teacher_subject__subject__name'].unique()

exams = ['p1', 'p2', 'p3', 'p4', 'p5', 'p6']
subjects = ['Arte e Literatura', 'Biologia', 'Ciências',
    'Geografia', 'História', 'Língua Portuguesa', 'Matemática',
    'Filosofia', 'Física', 'Gramática', 'Língua Inglesa*',
    'Química', 'Sociologia', 'História e Geografia',
    'Natureza e sociedade'
]
grades = ['f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'm1', 'm2', 'm3']

for exam in exams:
    for subject in subjects:
        for grade in grades:
            filtro = df['application__exam__name'].str.contains(grade.upper()) & df['application__exam__examteachersubject__teacher_subject__subject__name'].str.contains(subject) & df['application__exam__name'].str.contains(exam.upper())
            df_filtred = df[filtro]
            mean_grade = df_filtred['total_grade'].mean()
            if mean_grade:
                print(f'{exam},{subject},{grade},{mean_grade}')
