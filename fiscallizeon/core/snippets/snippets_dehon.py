from fiscallizeon.exams.models import Exam, ExamTeacherSubject, StatusQuestion, ExamQuestion
from decimal import Decimal

exams_name = [
    # "P1 - 2ª SÉRIE - QUIMICA / QUIMICA IT / GRAMATICA - 14/06 - EXATAS",
    # "P1 - ADAP - 2ª SÉRIE - QUIMICA / QUIMICA IT / GRAMATICA - 14/06 - EXATAS",
    # "P1 - ADAP - 2ª SÉRIE - BIOLOGIA / BIOLOGIA IT / INGLÊS - 21/06 - EXATAS",
    # "P1 - ADAP - 2ª SÉRIE - BIOLOGIA/ INGLÊS - 21/06 - HUMANAS",
    # "P1 - 2ª SÉRIE - BIOLOGIA / INGLÊS - 21/06 - HUMANAS",
    # "P1 - ADAP - 3ª SÉRIE - HISTORIA / HISTÓRIA IT / FISICA - 07/06 - HUMANAS",
    # "P1 - 3ª SÉRIE - HISTORIA / HISTÓRIA IT / FISICA - 07/06 - HUMANAS",
    # "P1 - ADAP - 3ª SÉRIE - HISTORIA / FISICA / FISICA IT - 07/06 - EXATAS",
    # "P1 - 3ª SÉRIE - HISTORIA / FISICA / FISICA IT - 07/06 - EXATAS",
    # "P1 - ADAP - 3ª SÉRIE - QUIMICA / INGLÊS - 29/05 - HUMANAS",
    # "P1 - 3ª SÉRIE - QUIMICA / INGLÊS - 29/05 - HUMANAS",
    # "P1 - ADAP - 3ª SÉRIE - QUIMICA / QUIMICA IT / INGLÊS - 29/05 - EXATAS",
    # "P1 - 3ª SÉRIE - QUIMICA / QUIMICA IT / INGLÊS - 29/05 - EXATAS",
    # "P1 - ADAP 2ª SÉRIE - MATEMATICA / MATEMATICA IT / GEOGRAFIA - 29/05 - EXATAS",
    # "P1 - 2ª SÉRIE - MATEMATICA / MATEMATICA IT / GEOGRAFIA - 29/05 - EXATAS",
    "P1 - 2ª SÉRIE - BIOLOGIA / BIOLOGIA IT / INGLÊS - 21/06 - EXATAS"
]

for exam in Exam.objects.filter(name__in=exams_name):
    status = StatusQuestion.objects.filter(
        active=True, 
        annuled_give_score=False,
        exam_question__exam=exam,
        status=StatusQuestion.ANNULLED,
    )
    print(status.count(), exam.name)
    for stat in status:
        stat.annuled_give_score = True
        stat.save(skip_hooks=True)



exams_name = [
    # ["P1 - ADAP - 2ª SÉRIE - QUIMICA / QUIMICA IT / GRAMATICA - 14/06 - EXATAS"	,"0.018947"],
    # ["P1 - ADAP - 2ª SÉRIE - BIOLOGIA / BIOLOGIA IT / INGLÊS - 21/06 - EXATAS" ,"0.045946"],
    # ["P1 - ADAP - 2ª SÉRIE - BIOLOGIA/ INGLÊS - 21/06 - HUMANAS" ,"0.028000"],
    # ["P1 - 2ª SÉRIE - BIOLOGIA / INGLÊS - 21/06 - HUMANAS"	,"0.028000"],
    # ["P1 - ADAP - 3ª SÉRIE - HISTORIA / HISTÓRIA IT / FISICA - 07/06 - HUMANAS" ,"0.013629"],
    # ["P1 - 3ª SÉRIE - HISTORIA / HISTÓRIA IT / FISICA - 07/06 - HUMANAS" ,"0.027272"],
    # ["P1 - ADAP - 3ª SÉRIE - HISTORIA / FISICA / FISICA IT - 07/06 - EXATAS" ,"0.013636"],
    ["d7f1525c-50d3-4cfd-b2fd-c593debaca4f" ,"0.013636"],
    # ["P1 - ADAP 2ª SÉRIE - MATEMATICA / MATEMATICA IT / GEOGRAFIA - 29/05 - EXATAS"	,"0.040540"],
    # ["P1 - 2ª SÉRIE - MATEMATICA / MATEMATICA IT / GEOGRAFIA - 29/05 - EXATAS" ,"0.062659"],
    # ["P1 - 2ª SÉRIE - BIOLOGIA / BIOLOGIA IT / INGLÊS - 21/06 - EXATAS", "0.045946"]
]

for exam_name in exams_name:
    exam = Exam.objects.filter(pk=exam_name[0]).first()
    if not exam:
        print(exam_name)
    exam_questions = ExamQuestion.objects.filter(
        exam=exam,
        block_weight=False
    ).order_by("exam_teacher_subject__order", "order")
    for exam_question in exam_questions:
        anulled = StatusQuestion.objects.filter(
            active=True,
            exam_question=exam_question,
            status=StatusQuestion.ANNULLED,
        ).exists()
        if anulled:
            continue
        print(exam_name, exam_question.weight, exam_question.weight - Decimal(exam_name[1]))
        exam_question.weight = exam_question.weight - Decimal(exam_name[1])
        exam_question.save(skip_hooks=True)


status = StatusQuestion.objects.filter(
    exam_question__exam__coordinations__unity__client__name__icontains="dehon",
    exam_question__exam__name__icontains="p1 -",
    status=StatusQuestion.ANNULLED,
    annuled_give_score=False,
    active=True
).distinct()

for stat in status:
    print(stat.exam_question.exam.name)


from django.db.models import Subquery, OuterRef, Value, Q, Case, When, F, DecimalField
from django.db.models.functions import Round
from fiscallizeon.answers.models import FileAnswer


files = FileAnswer.objects.filter(
    Q(
        Q(student_application__application__exam__name__icontains="p1 -"),
        Q(student_application__student__client__name__icontains="dehon")
    )
).annotate(
    question_weight=Subquery(
        ExamQuestion.objects.filter(
            question=OuterRef('question'),
            exam=OuterRef('student_application__application__exam')
        ).values('weight')[:1],
        output_field=DecimalField()
    )
).annotate(
    question_weight_round=Round('question_weight'),
    teacher_grade_round=Round('teacher_grade')
).filter(
    teacher_grade_round__gt=F('question_weight_round')
).distinct('pk')

for f in files:
    print(f'{f.question_weight_round}, {f.teacher_grade}, {f.student_application.application.exam}, {f.student_application.student.name}')




from fiscallizeon.applications.models import ApplicationStudent
from django.db.models import Q
apps = ApplicationStudent.objects.filter(
    Q(
        Q(student__client__name__icontains="deho"),
        Q(application__exam__name__istartswith="p1 -"),
    )
).get_annotation_count_answers(only_total_grade=True, exclude_annuleds=True).filter(
    total_grade__gt=30.009
).distinct()


for app in apps:
    print(f'{app.student.name}, {app.application.exam.name}, {app.total_grade}')




from fiscallizeon.answers.models import FileAnswer
from django.db.models import F, FloatField, Func


class Round(Func):
    function = 'ROUND'
    template = '%(function)s(%(expressions)s, 4)'
    output_field = FloatField()


exams_id = [
    "c43947c4-a902-44a8-b549-8607b046e19a",
    "fc9c79d6-bb09-4576-b636-8725b5445dc2",
]

files = FileAnswer.objects.filter(
    student_application__application__exam__pk__in=exams_id,
).annotate(
    question_weight=Subquery(
        ExamQuestion.objects.filter(
            question=OuterRef('question'),
            exam=OuterRef('student_application__application__exam')
        ).values('weight')[:1],
        output_field=DecimalField()
    )
).values_list('question_weight', 'teacher_grade').distinct()

for weight in files:
    print(weight[0], weight[1])


actual_weight = 1
before_weight = 1.045946
for grade in [round(before_weight*0.25, 4), round(before_weight*0.5, 4), round(before_weight*0.75, 4), round(before_weight*1, 4)]:
    files = FileAnswer.objects.filter(
        student_application__application__exam=exam_id,
    ).annotate(
        teacher_grade_round=Round('teacher_grade')
    ).filter(
        teacher_grade_round=grade
    )
    print(files.count(), grade, round(actual_weight*(grade/before_weight), 4))
    files.update(
        teacher_grade=round(actual_weight*(grade/before_weight), 4)
    )

from fiscallizeon.applications.models import ApplicationStudent

apps = ApplicationStudent.objects.filter(
    Q(
        Q(is_omr=False),
        Q(student__client__name__icontains="dehon"),
        Q(application__exam__name__istartswith="p1")
    ),
    Q(
        Q(file_answers__isnull=False) |
        Q(option_answers__isnull=False) |
        Q(textual_answers__isnull=False) |
        Q(sum_answers__isnull=False)
    )
).distinct()

for app in apps:
    print(f'{app.application.exam.name}, {app.student.name}')
    app.file_answers.all().delete()
    app.option_answers.all().delete()
    app.textual_answers.all().delete()
    app.sum_answers.all().delete()



#vericar alunos q acessaram indevidament


import json
from datetime import datetime
from fiscallizeon.applications.models import ApplicationStudent
from django.utils.timezone import make_aware
from django.utils import timezone
import csv
import json
import requests
from io import StringIO

# Baixar o conteúdo do CSV da URL
url = (
    "https://fiscallizeremote.nyc3.cdn.digitaloceanspaces.com/temp/apenas-rota-2025.csv"
)
response = requests.get(url)
response.encoding = "utf-8"

# Converter o conteúdo CSV em uma lista de dicionários
f = StringIO(response.text)
reader = csv.DictReader(f)
logs = list(reader)

for index, log in enumerate(logs):
    try:
        pk_application_student = log["path"].split("/")[4]
        data_hora_str = f"{log['date'][:10]} {log['time'][:5]}"
        data_hora = make_aware(datetime.strptime(data_hora_str, "%Y-%m-%d %H:%M"))
        application_student = ApplicationStudent.objects.get(pk=pk_application_student)
        data_hora_application = (
            timezone.localtime(application_student.application.date_time_start_tz).strftime("%Y-%m-%d %H:%M")
        )
        if application_student:
            if data_hora < application_student.application.date_time_start_tz:
                print(
                    f"{application_student.student.client},{data_hora_str},{application_student.student.name},{application_student.application.exam.name},{application_student.get_total_grade(include_give_score=True)},{application_student.application.exam.get_total_weight()},,{data_hora_application},{log['path']}"
                )
    except Exception as e:
        print(e)