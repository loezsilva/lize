import re
import io
import zipfile
import pandas as pd
import numpy as np

from django.utils import timezone
from django.db.models import F, DecimalField
from django.db.models.functions import Cast

from fiscallizeon.celery import app
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.exams.models import Exam
from fiscallizeon.subjects.models import Subject
from fiscallizeon.exports.models import ExportExams
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.clients.models import Unity
from fiscallizeon.accounts.models import User

def _pivot_df(df, extra_columns):
    index_colums = [
        'student__name', 'student__enrollment_number',
    ]

    if extra_columns:
        index_colums.extend(['school_class_name', 'school_class_unity'])

    index_colums.extend(['application__exam__name', 'application__date', 'application__start'])

    df = df.pivot_table(
        index=index_colums, columns='subject_name', values='total_grade'
    )

    df.reset_index(inplace=True)
    return df

def _rearrange_df(df):
    columns_order = [
        'student__name', 'student__enrollment_number', 'school_class_name', 'school_class_unity',
        'choice_grade_sum', 'discursive_grade', 'sum_questions_grade_sum', 'total_grade',
        'subject_name', 'application__exam__name', 'application__date', 'application__start'
    ]

    final_columns_order = sorted(
        df.columns, key=lambda x: columns_order.index(x) if x in columns_order else float('inf')
    )
    df = df[final_columns_order]

    df = df.rename(
        columns={
            'student__name': 'Aluno', 
            'student__enrollment_number': 'Matrícula',
            'application__exam__name': 'Caderno',
            'application__date': 'Data',
            'application__start': 'Hora',
            'choice_grade_sum': 'Nota objetivas',
            'discursive_grade': 'Nota discursivas',
            'sum_questions_grade_sum': 'Nota somatórias',
            'total_grade': 'Nota',
            'subject_name': 'Disciplina',
            'school_class_name': 'Turma',
            'school_class_unity': 'Unidade',
        },
    )

    return df

def get_application_student_queryset(exam, students_filter, school_class=None, unity=None, start_date=None, end_date=None, application_category=None):
    get_present = students_filter == ExportExams.PRESENT_STUDENTS
    get_vacant = students_filter == ExportExams.ABSENT_STUDENTS

    application_students_exam = ApplicationStudent.objects.get_unique_set(
        exam=exam, 
        present=get_present, 
        vacant=get_vacant
    )

    if start_date and end_date:
        application_students_exam = application_students_exam.filter(
            application__date__gte=start_date,
            application__date__lte=end_date
        )

    if school_class:
        application_students_exam = application_students_exam.filter(
            student__in=school_class.students.all()
        ).distinct()

    elif unity:
        application_students_exam = application_students_exam.filter(
            student__classes__coordination__unity=unity
        ).distinct()

    if application_category:
        application_students_exam = application_students_exam.filter(
            application__category=application_category
        )
    
    return application_students_exam

def get_application_student_grades_df(exam, application_students, subjects=None, extra_columns=False):
    if exam.is_abstract:
        local_subjects = Subject.objects.filter(question__in=exam.questions.all()).distinct()
    else:
        local_subjects = Subject.objects.filter(pk__in=exam.teacher_subjects.all().values_list('subject__pk', flat=True)).distinct()

    subjects = subjects or local_subjects
    queryset = application_students.get_annotation_count_answers(subjects=subjects, exclude_annuleds=True, include_give_score=False)

    columns_names = [
        'student__name', 
        'student__enrollment_number',
        'start_time',
        'choice_grade_sum',
        'discursive_grade',
        'sum_questions_grade_sum',
        'total_grade',
        'is_present',
        'application__date',
        'application__start'
    ]

    if extra_columns:
        columns_names.extend(['school_class_name', 'school_class_unity'])
        queryset = queryset.get_last_school_class(use_application_date=True)

    queryset = queryset.using('readonly').annotate(
        discursive_grade=Cast(
            F('textual_grade_sum') + F('file_grade_sum'),
            DecimalField(max_digits=10, decimal_places=6)
        ),
        sum_questions_grade_sum=Cast(F('sum_questions_grade_sum'),
            DecimalField(max_digits=10, decimal_places=6)
        ),
        total_grade=Cast(F('total_grade'),
            DecimalField(max_digits=10, decimal_places=6)
        ),
    )

    if queryset.exists():
        df = pd.DataFrame(queryset.values(*columns_names))
        df.loc[~df['is_present'], ['choice_grade_sum', 'discursive_grade', 'sum_questions_grade_sum', 'total_grade']] = np.nan
        df['total_grade'] = df['total_grade'].fillna('Ausente')
    else:
        df = pd.DataFrame(columns=columns_names)

    return df

def get_application_student_subject_grades_df(exam, application_students, subjects=None, extra_columns=False):
    exam_subjects = Subject.objects.filter(pk__in=exam.teacher_subjects.all().values_list('subject__pk', flat=True)).distinct()
    if exam.is_abstract:
        exam_subjects = Subject.objects.filter(question__in=exam.questions.all()).distinct()

    if subjects:
        exam_subjects.filter(pk__in=subjects)

    columns_names = [
        'student__name', 
        'student__enrollment_number',
        'start_time',
        'total_grade',
        'is_present',
        'application__date',
        'application__start'
    ]

    if extra_columns:
        columns_names.extend(['school_class_name', 'school_class_unity'])
        application_students = application_students.get_last_school_class(use_application_date=True)

    dataframes = []
    for subject in exam_subjects:
        _df = pd.DataFrame(application_students.get_annotation_count_answers([subject], only_total_grade=True, exclude_annuleds=True).values(*columns_names))
        _df['subject_name'] = subject.name
        dataframes.append(_df)

    return pd.concat(dataframes, ignore_index=True)

@app.task(bind=True)
def export_exams_erp(
        self, user_id, exam_pks=[], school_class_pk=None, 
        unity_pk=None, students_filter=None, application_category=None,
        subjects_pks=[], subjects_format=ExportExams.SUBJECT_GRADES_SUMMED,
        extra_columns=False, file_format=ExportExams.FORMAT_CSV,
        start_date=None, end_date=None, add_exam_name=False,
        export_standard='fiscallize', unique_file=False, get_abstracts=False
    ):

    exams = Exam.objects.filter(pk__in=exam_pks)
    user = User.objects.get(id=user_id)

    subjects = Subject.objects.filter(pk__in=subjects_pks)
    school_class = SchoolClass.objects.filter(pk=school_class_pk).first()
    unity = Unity.objects.filter(pk=unity_pk).first()

    self.update_state(state='PROGRESS', meta={'done': 0, 'total': exams.count()})

    dataframes_dicts = []
    total_exams = exams.count()
    for i, exam in enumerate(exams):
        application_students = (
            get_application_student_queryset(
                exam, students_filter, school_class, unity, start_date, end_date, application_category
            )
            .filter(
                student__classes__coordination__in=user.get_coordinations_cache(),
            )
        )

        if subjects_format == ExportExams.SUBJECT_GRADES_SUMMED:
            application_student_grades_df = get_application_student_grades_df(
                exam, application_students, subjects, extra_columns
            )
        else:
            application_student_grades_df = get_application_student_subject_grades_df(
                exam, application_students, subjects, extra_columns
            )

        application_student_grades_df['application__exam__name'] = exam.name

        if not application_student_grades_df.empty:
            application_student_grades_df.drop('start_time', axis=1, inplace=True)
            application_student_grades_df.drop('is_present', axis=1, inplace=True)

        dataframes_dicts.append({'exam': exam, 'df': application_student_grades_df})
        self.update_state(state='PROGRESS', meta={'done': i, 'total': total_exams})

    final_dfs = []
    if unique_file:
        df = pd.concat([d['df'] for d in dataframes_dicts], ignore_index=True)

        if subjects_format == ExportExams.SUBJECT_GRADES_COLUMNS:
            df = _pivot_df(df, extra_columns)

        df = _rearrange_df(df)
        final_dfs.append({'exam': 'all', 'df': df})
    else:
        for exam_dict in dataframes_dicts:
            if subjects_format == ExportExams.SUBJECT_GRADES_COLUMNS:
                exam_dict['df'] = _pivot_df(exam_dict['df'], extra_columns)

            exam_dict['df'] = _rearrange_df(exam_dict['df'])
            final_dfs.append(exam_dict)

    fs = PrivateMediaStorage()
    now = timezone.localtime(timezone.now())
    task_id = re.sub('\D', '', self.request.id)

    # Demanda da task: https://app.clickup.com/t/86a9p1d3e
    # Alguns clientes não estão conseguindo ver os dados do zip
    # Eu removi a geração do ZIP quando é apenas um caderno ou quando é geração em um arquivo único
    if len(final_dfs) == 1 or unique_file:
        df = final_dfs[0]['df']
        exam_name = 'cadernos' if unique_file else final_dfs[0]['exam'].name
        exam_name_safe = exam_name.replace('/', '')
        
        if not add_exam_name:
            df.drop('Caderno', axis=1, inplace=True)

        if file_format == ExportExams.FORMAT_CSV:
            df_buffer = io.StringIO()
            df.to_csv(df_buffer, index=False)
            content = df_buffer.getvalue().encode()
            ext = 'csv'
        else:
            df_buffer = io.BytesIO()
            df.to_excel(df_buffer, index=False, engine='openpyxl')
            content = df_buffer.getvalue()
            ext = 'xlsx'

        filename = fs.save(f'devolutivas/resultados/{exam_name_safe}_{now:%Y%m%d-%H%M%S}.{ext}', io.BytesIO(content))
        self.update_state(state='SUCCESS', meta=fs.url(filename))
        return fs.url(filename)

    # Caso contrário, zipa normalmente
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for df_dict in final_dfs:
            df = df_dict['df']
            exam_name = df_dict['exam'].name
            exam_name_safe = exam_name.replace('/', '')

            if not add_exam_name:
                df.drop('Caderno', axis=1, inplace=True)

            if file_format == ExportExams.FORMAT_CSV:
                df_buffer = io.StringIO()
                df.to_csv(df_buffer, index=False)
                content = df_buffer.getvalue().encode()
            else:
                df_buffer = io.BytesIO()
                df.to_excel(df_buffer, index=False, engine='openpyxl')
                content = df_buffer.getvalue()

            zip_file.writestr(f'{exam_name_safe}.{file_format}', content)

    filename = fs.save(f'devolutivas/resultados/{task_id}_{now:%Y%m%d-%H%M%S}.zip', zip_buffer)
    self.update_state(state='SUCCESS', meta=fs.url(filename))
    return fs.url(filename)