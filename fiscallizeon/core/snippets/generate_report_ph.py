import csv

from django.db.models import Subquery, OuterRef, Case, When, F, DecimalField, CharField, Value
from django.db.models.functions import Coalesce

from fiscallizeon.answers.models import FileAnswer, OptionAnswer, TextualAnswer
from fiscallizeon.exams.models import Exam, ExamQuestion
from fiscallizeon.classes.models import SchoolClass

exam = Exam.objects.get(pk='aa000485-1375-4a13-8043-4db1519cc7ac') #03/07
# exam = Exam.objects.get(pk='a5603ccb-fd7f-4fac-9349-766079daa029') #10/07

exam_questions = list(ExamQuestion.objects.filter(
    exam=exam
).distinct().order_by(
    'exam_teacher_subject__order', 'order'
).values_list(
    'question__pk',
))
exam_questions = [i[0] for i in exam_questions]

school_class_subquery = SchoolClass.objects.filter(
    students__pk=OuterRef('student_application__student__pk')
).distinct()

option_exam_question_subquery = ExamQuestion.objects.filter(
    question=OuterRef('question_option__question'),
    exam=OuterRef('student_application__application__exam')
)

exam_question_subquery = ExamQuestion.objects.filter(
    question=OuterRef('question'),
    exam=OuterRef('student_application__application__exam')
)

option_answers = OptionAnswer.objects.filter(
    student_application__application__exam=exam,
    status=OptionAnswer.ACTIVE
).annotate(
    question_subject=Subquery(option_exam_question_subquery.values(
        'exam_teacher_subject__teacher_subject__subject__name')    
    ),
    grade=Case(
        When(
            question_option__is_correct=True,
            then=Subquery(option_exam_question_subquery.values('weight'))
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
).values(
    'student_application__student__enrollment_number',
    'student_application__student__name',
    'student_application__application__exam__name',
    'school_class',
    'unity',
    'question_subject',
    'grade',
    'question_pk',
    'exam_question_sequence',
)

textual_answers = TextualAnswer.objects.filter(
    student_application__application__exam=exam
).annotate(    
    question_subject=Subquery(exam_question_subquery.values(
        'exam_teacher_subject__teacher_subject__subject__name')
    ),
    grade=Coalesce(F('teacher_grade'), Value(0, output_field=DecimalField())),
    school_class=school_class_subquery.values('name')[:1],
    unity=school_class_subquery.values('coordination__unity__name')[:1],
    question_pk=F('question__pk'),
    exam_question_sequence=Subquery(exam_question_subquery.annotate(
            sequence=(100 * (F('exam_teacher_subject__order') + 1)) + (F('order') + 1)
        ).values('sequence')
    ),
).values(
    'student_application__student__enrollment_number',
    'student_application__student__name',
    'student_application__application__exam__name',
    'school_class',
    'unity',
    'question_subject',
    'grade',
    'question_pk',
    'exam_question_sequence',
)


file_answers = FileAnswer.objects.filter(
    student_application__application__exam=exam
).annotate(    
    question_subject=Subquery(exam_question_subquery.values(
        'exam_teacher_subject__teacher_subject__subject__name')
    ),
    grade=Coalesce(F('teacher_grade'), Value(0, output_field=DecimalField())),
    school_class=school_class_subquery.values('name')[:1],
    unity=school_class_subquery.values('coordination__unity__name')[:1],
    question_pk=F('question__pk'),
    exam_question_sequence=Subquery(exam_question_subquery.annotate(
            sequence=(100 * (F('exam_teacher_subject__order') + 1)) + (F('order') + 1)
        ).values('sequence')
    ),
).values(
    'student_application__student__enrollment_number',
    'student_application__student__name',
    'student_application__application__exam__name',
    'school_class',
    'unity',
    'question_subject',
    'grade',
    'question_pk',
    'exam_question_sequence',
)

final_report = option_answers.union(textual_answers).order_by(
    'student_application__student__name', 'exam_question_sequence'
)

with open('ph_provas.csv', mode='w') as csv_file:
    report_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
    report_writer.writerow(['matricula', 'nome', 'unidade', 'turma', 'prova', 'disciplina', 'questao', 'nota', 'criado'])

    for answer in final_report:
        report_writer.writerow([
            answer["student_application__student__enrollment_number"],
            answer["student_application__student__name"],
            answer["unity"],
            answer["school_class"],
            answer["student_application__application__exam__name"],
            answer["question_subject"],
            f'Questão {exam_questions.index(answer["question_pk"]) + 1}',
            # 'ABCDEFGHI'[answer["index_alternative"]],
            answer["grade"]
        ])