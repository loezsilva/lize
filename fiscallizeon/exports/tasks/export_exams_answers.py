from asyncio import QueueEmpty
import re
import io
import sys, os
import csv
import zipfile
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.questions.models import Question

import pyexcel

from django.utils import timezone
from django.db.models import F, Subquery, OuterRef, Case, When, Value, DecimalField, CharField
from django.db.models.functions import Coalesce
from django.utils import timezone

from fiscallizeon.celery import app
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.answers.models import OptionAnswer, FileAnswer, TextualAnswer
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.exams.models import Exam, ExamQuestion
from fiscallizeon.exports.models import ExportExams
from fiscallizeon.accounts.models import User


school_class_subquery = SchoolClass.objects.filter(
    students__pk=OuterRef('student_application__student__pk'),
    school_year=OuterRef('student_application__application__date__year'),
    temporary_class=False,
).distinct()

exam_question_subquery = ExamQuestion.objects.filter(
    question=OuterRef('question'),
    exam=OuterRef('student_application__application__exam')
)

def get_exam_questions(exam):
    exam_questions = list(ExamQuestion.objects.filter(
            exam=exam
        ).availables().distinct().order_by(
            'exam_teacher_subject__order', 'order'
        ).values_list(
            'question__pk',
        )
    )
    return [i[0] for i in exam_questions]

def get_option_answers(exam, application_student=None):
    option_exam_question_subquery = ExamQuestion.objects.filter(
        question=OuterRef('question_option__question'),
        exam=OuterRef('student_application__application__exam')
    )

    queryset = OptionAnswer.objects.filter(
        student_application__application__exam=exam,
        status=OptionAnswer.ACTIVE,
    ).annotate(
        question_subject=Case(
            When(
                student_application__application__exam__is_abstract=True,
                then=Value('question_option__question__subject__name')
            ),
            default=Subquery(option_exam_question_subquery.values(
                'exam_teacher_subject__teacher_subject__subject__name')
            ),
            output_field=CharField()
        ),
        teacher_name=Case(
            When(
                student_application__application__exam__is_abstract=True,
                then=Value('-')
            ),
            default=Subquery(option_exam_question_subquery.values(
                'exam_teacher_subject__teacher_subject__teacher__name')
            ),
            output_field=CharField()
        ),
        question_weight=Subquery(option_exam_question_subquery.values('weight')),
        total_grade=Case(
            When(
                question_option__is_correct=True,
                then=F('question_weight')
            ),
            default=Value(0),
            output_field=DecimalField(),
        ),
        school_class=school_class_subquery.values('name')[:1],
        unity=school_class_subquery.values('coordination__unity__name')[:1],
        question_pk=F('question_option__question__pk'),
        exam_question_sequence=Subquery(option_exam_question_subquery.annotate(
                sequence=(100 * (F('exam_teacher_subject__order') + 1)) + (F('order') + 1)
            ).values('sequence')
        ),
        result=Case(
            When(
                question_option__is_correct=True,
                then=Value('Acerto')
            ),
            default=Value('Erro'),
            output_field=CharField()
        ),
        alternative=F('question_option__index'),
        questions_count=Value(exam.questions.count()),
        is_omr=F('student_application__is_omr'),
        question_level=F('question_option__question__level')
    ).values(
        'student_application__student__enrollment_number',
        'student_application__student__name',
        'student_application__application__exam__name',
        'school_class',
        'unity',
        'question_subject',
        'total_grade',
        'question_pk',
        'exam_question_sequence',
        'result',
        'alternative',
        'created_at',
        'questions_count',
        'is_omr',
        'question_level',
        'teacher_name'
    )

    if application_student:
        queryset = queryset.filter(student_application=application_student)

    return queryset

def get_textual_answers(exam, application_student=None):
    queryset = TextualAnswer.objects.filter(
        student_application__application__exam=exam,
    ).annotate(
        question_subject=F('exam_question__exam_teacher_subject__teacher_subject__subject__name'),
        teacher_name=F('exam_question__exam_teacher_subject__teacher_subject__teacher__name'),
        question_weight=F('exam_question__weight'),
        total_grade=Coalesce(F('grade') * F('question_weight'), Value(0, output_field=DecimalField())),
        school_class=school_class_subquery.values('name')[:1],
        unity=school_class_subquery.values('coordination__unity__name')[:1],
        question_pk=F('question__pk'),
        exam_question_sequence=Subquery(exam_question_subquery.annotate(
                sequence=(100 * (F('exam_teacher_subject__order') + 1)) + (F('order') + 1)
            ).values('sequence')
        ),
        result=Case(
            When(
                who_corrected__isnull=True,
                then=Value('Sem correção')
            ),
            When(
                grade__gt=Value(0),
                who_corrected__isnull=False,
                then=Value('Acerto')
            ),
            default=Value('Erro'),
            output_field=CharField()
        ),
        alternative=Value(-1),
        questions_count=Value(exam.questions.count()),
        is_omr=F('student_application__is_omr'),
        question_level=F('question__level')
    ).values(
        'student_application__student__enrollment_number',
        'student_application__student__name',
        'student_application__application__exam__name',
        'school_class',
        'unity',
        'question_subject',
        'total_grade',
        'question_pk',
        'exam_question_sequence',
        'result',
        'alternative',
        'created_at',
        'questions_count',
        'is_omr',
        'question_level',
        'teacher_name'
    )

    if application_student:
        queryset = queryset.filter(student_application=application_student)
    
    return queryset

def get_file_answers(exam, application_student=None):
    queryset = FileAnswer.objects.filter(
        student_application__application__exam=exam,
    ).annotate(    
        question_subject=F('exam_question__exam_teacher_subject__teacher_subject__subject__name'),
        teacher_name=F('exam_question__exam_teacher_subject__teacher_subject__teacher__name'),
        question_weight=F('exam_question__weight'),
        total_grade=Coalesce(F('grade') * F('question_weight'), Value(0, output_field=DecimalField())),
        school_class=school_class_subquery.values('name')[:1],
        unity=school_class_subquery.values('coordination__unity__name')[:1],
        question_pk=F('question__pk'),
        exam_question_sequence=Subquery(exam_question_subquery.annotate(
                sequence=(100 * (F('exam_teacher_subject__order') + 1)) + (F('order') + 1)
            ).values('sequence')
        ),
        result=Case(
            When(
                who_corrected__isnull=True,
                then=Value('Sem correção')
            ),
            When(
                grade__gt=Value(0),
                who_corrected__isnull=True,
                then=Value('Acerto')
            ),
            default=Value('Erro'),
            output_field=CharField()
        ),
        alternative=Value(-1),
        questions_count=Value(exam.questions.count()),
        is_omr=F('student_application__is_omr'),
        question_level=F('question__level')
    ).values(
        'student_application__student__enrollment_number',
        'student_application__student__name',
        'student_application__application__exam__name',
        'school_class',
        'unity',
        'question_subject',
        'total_grade',
        'question_pk',
        'exam_question_sequence',
        'result',
        'alternative',
        'created_at',
        'questions_count',
        'is_omr',
        'question_level',
        'teacher_name'
    )

    if application_student:
        queryset = queryset.filter(student_application=application_student)

    return queryset

def get_queryset(user, exam, start_date, end_date, application_student=None):
    option_answers = get_option_answers(exam, application_student=application_student)
    textual_answers = get_textual_answers(exam, application_student=application_student)
    file_answers = get_file_answers(exam, application_student=application_student)

    if start_date and end_date:
        option_answers = option_answers.filter(
            student_application__application__date__gte=start_date,
            student_application__application__date__lte=end_date,
            student_application__student__classes__coordination__in=user.get_coordinations_cache(),
        )
        textual_answers = textual_answers.filter(
            student_application__application__date__gte=start_date,
            student_application__application__date__lte=end_date,
            student_application__student__classes__coordination__in=user.get_coordinations_cache(),
        )
        file_answers = file_answers.filter(
            student_application__application__date__gte=start_date,
            student_application__application__date__lte=end_date,
            student_application__student__classes__coordination__in=user.get_coordinations_cache(),
        )

    return option_answers.union(textual_answers).union(file_answers).order_by(
        'student_application__student__name', 'exam_question_sequence'
    )

def write_exam_students_lines(writer, user, exam, start_date, end_date, add_topic=False, add_bncc=False, add_teacher_name=False):
    exam_questions = get_exam_questions(exam)

    answers = get_queryset(user, exam, start_date, end_date)
    for answer in answers:
        try:
            row = [
                answer['student_application__student__enrollment_number'],
                answer['student_application__student__name'],
                answer['unity'],
                answer['school_class'],
                answer['student_application__application__exam__name'],
                'Presencial' if answer['is_omr'] else 'Remoto', 
                answer['question_subject'],
                f'Questão {exam_questions.index(answer["question_pk"]) + 1}',
                answer['total_grade'],
                answer['result'],
                answer['alternative'] if answer['alternative'] >= 0 else '',
                answer['created_at'],
                answer['questions_count'],
                answer['question_level']
            ]

            if add_topic:
                question = Question.objects.get(pk=answer["question_pk"])
                topics = question.topics.all()
                row.insert(len(row)-5, "|".join([topic.name for topic in topics]) if topics else "Sem assunto")

            if add_bncc:
                question = Question.objects.get(pk=answer["question_pk"])
                abilities = question.abilities.all()
                competences = question.competences.all()
                row.insert(len(row)-5, "|".join([abilitie.text for abilitie in abilities]) if abilities else "Sem habilidade")
                row.insert(len(row)-5, "|".join([competence.text for competence in competences]) if competences else "Sem competência")

            if add_teacher_name:
                row.extend(
                    [answer['teacher_name']]
                )

            writer.writerow(row)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

def write_questions_columns(writer, user, exam, start_date, end_date, only_correct_wrong=False):
    exam_questions = get_exam_questions(exam)
    header = ['matricula', 'nome', 'unidade', 'turma', 'prova', 'lingua_estrangeira']
    header.extend([f'Questão {i}' for i, q in enumerate(exam_questions, 1)])
    writer.writerow(header)
    application_students = ApplicationStudent.objects.filter(
        application__exam=exam,
        student__classes__coordination__in=user.get_coordinations_cache(),
    ).distinct()
    
    for application_student in application_students:
        student_class = application_student.get_last_class_student()
        row_data = [
            application_student.student.enrollment_number,
            application_student.student.name,
            student_class.coordination.unity.name if student_class else '-',
            student_class.name if student_class else '-',
            application_student.application.exam.name,
            application_student.get_foreign_language_display() or '-',
        ]

        answers = list(get_queryset(user, exam, start_date, end_date, application_student=application_student))
        questions_results = []
        for exam_question in exam_questions:
            try:
                alternative = next(filter(lambda answer: answer['question_pk'] == exam_question, answers))
                if not only_correct_wrong:
                    questions_results.append(
                        alternative.get('alternative')
                    )
                else:
                    result = alternative.get('result')
                    questions_results.append(
                        "1" if result == "Acerto" else "0"  
                    )
            except IndexError:
                questions_results.append('')
            except StopIteration:
                questions_results.append('')

        row_data.extend(questions_results)
        writer.writerow(row_data)

@app.task(bind=True)
def export_exams_answers(
        self, user_id, exam_pks=[], start_date=None, end_date=None, add_topic=False, add_bncc=False,
        file_format=ExportExams.FORMAT_CSV, export_disposition=ExportExams.EXPORT_ROWS, only_correct_wrong=False, add_teacher_name=False
    ):

    buffer = io.StringIO()  
    writer = csv.writer(
        buffer, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL
    )

    exams = Exam.objects.filter(pk__in=exam_pks)
    user = User.objects.get(id=user_id)

    if not exams:
        self.update_state(state='SUCCESS')
        return None

    self.update_state(state='PROGRESS', meta={'done': 0, 'total': exams.count()})

    columns = []

    if export_disposition == ExportExams.EXPORT_ROWS:
        columns = ['matricula', 'nome', 'unidade', 'turma', 'prova', 'tipo', 'disciplina', 'questao', 'nota', 'resultado', 'alternativa', 'criado', 'total_questoes_prova', 'dificuldade'
        ]

        if add_topic:
            columns.insert(len(columns)-5, "assunto")

        if add_bncc:
            columns.insert(len(columns)-5, "habilidades")
            columns.insert(len(columns)-5, "competencias")

        if add_teacher_name:
            columns.append("Nome do professor")

        writer.writerow(columns)

    for i, exam in enumerate(exams, start=1):
        if export_disposition == ExportExams.EXPORT_ROWS:
            write_exam_students_lines(writer, user, exam, start_date, end_date, add_topic, add_bncc, add_teacher_name)
        else:
            write_questions_columns(writer, user, exam, start_date, end_date, only_correct_wrong)

        self.update_state(state='PROGRESS', meta={'done': i, 'total': exams.count()})
    
    buffer.seek(0)
    sheet = pyexcel.load_from_memory('csv', buffer.getvalue())
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED, False) as zip_file:
        if file_format == ExportExams.FORMAT_CSV:
            zip_file.writestr('exportação de respostas.csv', sheet.csv.encode('utf-8'))
        else:
            zip_file.writestr(f'exportação de respostas.xls', sheet.xls)
    
    fs = PrivateMediaStorage()
    now = timezone.localtime(timezone.now())
    task_id = re.sub('\D', '', self.request.id)

    filename = fs.save(
        f'devolutivas/resultados/{task_id}_{now:%Y%m%d-%H%M%S}.zip', 
        zip_buffer
    )
    
    self.update_state(state='SUCCESS', meta=fs.url(filename))
    return fs.url(filename)