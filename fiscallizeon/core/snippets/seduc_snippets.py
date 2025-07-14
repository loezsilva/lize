from fiscallizeon.exams.models import ExamTeacherSubject, StatusQuestion
from django.db.models import Q
ets = ExamTeacherSubject.objects.filter(
    exam__coordinations__unity__client__name__icontains="seduc"
).distinct()
for e in ets:
    # APPROVED
    # REPROVED
    # OPENED
    # CORRECTION_PENDING
    # CORRECTED
    # ANNULLED
    # USE_LATER
    # DRAFT
    approved = e.examquestion_set.filter(
        statusquestion__active=True, 
        statusquestion__status=StatusQuestion.APPROVED
    ).count()
    reproved = e.examquestion_set.filter(
        statusquestion__active=True, 
        statusquestion__status=StatusQuestion.REPROVED
    ).count()
    opened = e.examquestion_set.filter(
         Q(
            Q(
                statusquestion__active=True, 
                statusquestion__status=StatusQuestion.OPENED
            ) |
            Q(
                statusquestion__isnull=True
            )
        )
        
    ).count()
    correction_pending = e.examquestion_set.filter(
        statusquestion__active=True, 
        statusquestion__status=StatusQuestion.CORRECTION_PENDING
    ).count()
    corrected = e.examquestion_set.filter(
        statusquestion__active=True, 
        statusquestion__status=StatusQuestion.CORRECTED
    ).count()
    annulled = e.examquestion_set.filter(
        statusquestion__active=True, 
        statusquestion__status=StatusQuestion.ANNULLED
    ).count()
    use_later = e.examquestion_set.filter(
        statusquestion__active=True, 
        statusquestion__status=StatusQuestion.USE_LATER
    ).count()
    draft = e.examquestion_set.filter(
        statusquestion__active=True, 
        statusquestion__status=StatusQuestion.DRAFT
    ).count()
    print(f'{e.exam.name};{e.exam.get_status_display()};{e.exam.elaboration_deadline};{e.teacher_subject.teacher.name};{e.teacher_subject.subject.name};{e.quantity};{approved};{reproved};{opened};{correction_pending};{corrected};{annulled};{use_later};{draft}')


from fiscallizeon.exams.models import ExamTeacherSubject, StatusQuestion
from django.db.models import Q
ets = ExamTeacherSubject.objects.filter(
    exam__coordinations__unity__client__name__icontains="seduc"
).distinct()
for e in ets:
    # APPROVED
    # REPROVED
    # OPENED
    # CORRECTION_PENDING
    # CORRECTED
    # ANNULLED
    # USE_LATER
    # DRAFT
    approved = e.examquestion_set.filter(
        statusquestion__active=True, 
        statusquestion__status=StatusQuestion.APPROVED
    ).count()
    reproved = e.examquestion_set.filter(
        statusquestion__active=True, 
        statusquestion__status=StatusQuestion.REPROVED
    ).count()
    opened = e.examquestion_set.filter(
         Q(
            Q(
                statusquestion__active=True, 
                statusquestion__status=StatusQuestion.OPENED
            ) |
            Q(
                statusquestion__isnull=True
            )
        )
        
    ).count()
    correction_pending = e.examquestion_set.filter(
        statusquestion__active=True, 
        statusquestion__status=StatusQuestion.CORRECTION_PENDING
    ).count()
    corrected = e.examquestion_set.filter(
        statusquestion__active=True, 
        statusquestion__status=StatusQuestion.CORRECTED
    ).count()
    annulled = e.examquestion_set.filter(
        statusquestion__active=True, 
        statusquestion__status=StatusQuestion.ANNULLED
    ).count()
    use_later = e.examquestion_set.filter(
        statusquestion__active=True, 
        statusquestion__status=StatusQuestion.USE_LATER
    ).count()
    draft = e.examquestion_set.filter(
        statusquestion__active=True, 
        statusquestion__status=StatusQuestion.DRAFT
    ).count()
    print(f'{e.exam.name};{e.exam.get_status_display()};{e.exam.elaboration_deadline};{e.teacher_subject.teacher.name};{e.teacher_subject.subject.name};{e.quantity};{approved};{reproved};{opened};{correction_pending};{corrected};{annulled};{use_later};{draft}')


data = [
    [
        "3ª série EM_PROVA PAULISTA 2BI_IT M/CN_DIA 1",
        "2025 - PP - FGB - 2º ciclo - Médio - 3ª série - Dia 1 ",
        "2025 - PP - IT M/CN - 2º ciclo - Médio - 3ª série - Dia 1 ",
        "OE - 2º ciclo - Médio - 3ª série - Dia 1",
        "",
    ],
    [
        "3ª série EM_PROVA PAULISTA 2BI_IT LG/CH_DIA 1",
        "2025 - PP - FGB - 2º ciclo - Médio - 3ª série - Dia 1 ",
        "2025 - PP - IT LG/CH - 2º ciclo - Médio - 3ª série - Dia 1 ",
        "OE - 2º ciclo - Médio - 3ª série - Dia 1",
        "",
    ],
    [
        "3ª série EM_PROVA PAULISTA 2BI_IT M/CN_DIA 2",
        "2025 - PP - FGB - 2º ciclo - Médio - 3ª série - Dia 2",
        "2025 - PP - IT M/CN - 2º ciclo - Médio - 3ª série - Dia 2 ",
        "OE - 2º ciclo - Médio - 3ª série - Dia 2",
        "",
    ],
    [
        "3ª série EM_PROVA PAULISTA 2BI_IT LG/CH_DIA 2",
        "2025 - PP - FGB - 2º ciclo - Médio - 3ª série - Dia 2",
        "2025 - PP - IT LG/CH - 2º ciclo - Médio - 3ª série - Dia 2 ",
        "OE - 2º ciclo - Médio - 3ª série - Dia 2",
        "",
    ],
    [
        "3ª série EM_EXPANSÃO_PROVA PAULISTA 2BI_IT M/CN_DIA 1",
        "2025 - PP - FGB - 2º ciclo - Médio - 3ª série - NOTURNO - Dia 1 ",
        "2025 - PP - IT M/CN - 2º ciclo - Médio - 3ª série - Dia 1 ",
        "OE - 2º ciclo - Médio - 3ª série - Dia 1",
        "",
    ],
    [
        "3ª série EM_EXPANSÃO_PROVA PAULISTA 2BI_IT LG/CH_DIA 1",
        "2025 - PP - FGB - 2º ciclo - Médio - 3ª série - NOTURNO - Dia 1 ",
        "2025 - PP - IT LG/CH - 2º ciclo - Médio - 3ª série - Dia 1 ",
        "OE - 2º ciclo - Médio - 3ª série - Dia 1",
        "",
    ],
    [
        "3ª série EM_EXPANSÃO_PROVA PAULISTA 2BI_IT M/CN_DIA 2",
        "2025 - PP - FGB - 2º ciclo - Médio - 3ª série - NOTURNO - Dia 2",
        "2025 - PP - IT M/CN - 2º ciclo - Médio - 3ª série - Dia 2 ",
        "OE - 2º ciclo - Médio - 3ª série - Dia 2",
        "",
    ],
    [
        "3ª série EM_EXPANSÃO_PROVA PAULISTA 2BI_IT LG/CH_DIA 2",
        "2025 - PP - FGB - 2º ciclo - Médio - 3ª série - NOTURNO - Dia 2",
        "2025 - PP - IT LG/CH - 2º ciclo - Médio - 3ª série - Dia 2 ",
        "OE - 2º ciclo - Médio - 3ª série - Dia 2",
        "",
    ],
    [
        "3ª série EM_PROVA PAULISTA 2BI_EP_ADMINISTRAÇÃO_DIA 1 - COM OE",
        "2025 - PP - FGB - 2º ciclo - Médio - 3ª série - Dia 1 ",
        "3ª série EM_PROVA PAULISTA_2º BI_EP_ADMINISTRAÇÃO_DIA 1",
        "OE - 2º ciclo - Médio - 3ª série - Dia 1",
        "",
    ],
    [
        "3ª série EM_PROVA PAULISTA 2BI_EP_AGRONEGÓCIO_DIA 1 - COM OE",
        "2025 - PP - FGB - 2º ciclo - Médio - 3ª série - Dia 1 ",
        "3ª série EM_PROVA PAULISTA_2º BI_EP_AGRONEGÓCIO_DIA 1",
        "PM_2º BI_EP_AGRONEGÓCIO_DIA 1",
        "OE - 2º ciclo - Médio - 3ª série - Dia 1",
    ],
    [
        "3ª série EM_PROVA PAULISTA 2BI_EP_CIÊNCIA DE DADOS_DIA 1 - COM OE",
        "2025 - PP - FGB - 2º ciclo - Médio - 3ª série - Dia 1 ",
        "3ª série EM_PROVA PAULISTA_2º BI_EP_CIÊNCIA DE DADOS_DIA 1",
        "PM_2º BI_EP_CIENCIA DE DADOS_DIA 1",
        "OE - 2º ciclo - Médio - 3ª série - Dia 1",
    ],
    [
        "3ª série EM_PROVA PAULISTA 2BI_EP_DESENVOLVIMENTO DE SISTEMAS_DIA 1 - COM OE",
        "2025 - PP - FGB - 2º ciclo - Médio - 3ª série - Dia 1 ",
        "3ª série EM_PROVA PAULISTA_2º BI_EP_DESENVOLVIMENTO DE SISTEMAS_DIA 1",
        "PM_2º BI_EP_DESENVOLVIMENTO DE SISTEMAS_DIA 1",
        "OE - 2º ciclo - Médio - 3ª série - Dia 1",
    ],
    [
        "3ª série EM_PROVA PAULISTA 2BI_EP_ENFERMAGEM_DIA 1 - COM OE",
        "2025 - PP - FGB - 2º ciclo - Médio - 3ª série - Dia 1 ",
        "3ª série EM_PROVA PAULISTA_2º BI_EP_ENFERMAGEM_DIA 1",
        "PM_2º BI_EP_ENFERMAGEM_DIA 1",
        "OE - 2º ciclo - Médio - 3ª série - Dia 1",
    ],
    [
        "3ª série EM_PROVA PAULISTA 2BI_EP_FARMÁCIA_DIA 1 - COM OE",
        "2025 - PP - FGB - 2º ciclo - Médio - 3ª série - Dia 1 ",
        "3ª série EM_PROVA PAULISTA_2º BI_EP_FARMÁCIA_DIA 1",
        "PM_2º BI_EP_FARMÁCIA_DIA 1",
        "OE - 2º ciclo - Médio - 3ª série - Dia 1",
    ],
    [
        "3ª série EM_PROVA PAULISTA 2BI_EP_HOTELARIA_DIA 1 - COM OE",
        "2025 - PP - FGB - 2º ciclo - Médio - 3ª série - Dia 1 ",
        "3ª série EM_PROVA PAULISTA_2º BI_EP_HOTELARIA_DIA 1",
        "PM_2º BI_EP_HOTEL_DIA 1",
        "OE - 2º ciclo - Médio - 3ª série - Dia 1",
    ],
    [
        "3ª série EM_PROVA PAULISTA 2BI_EP_LOGÍSTICA_DIA 1 - COM OE",
        "2025 - PP - FGB - 2º ciclo - Médio - 3ª série - Dia 1 ",
        "3ª série EM_PROVA PAULISTA_2º BI_EP_LOGÍSTICA_DIA 1",
        "PM_2º BI_EP_LOGÍSTICA_DIA 1",
        "OE - 2º ciclo - Médio - 3ª série - Dia 1",
    ],
    [
        "3ª série EM_PROVA PAULISTA 2BI_EP_VENDAS_DIA 1 - COM OE",
        "2025 - PP - FGB - 2º ciclo - Médio - 3ª série - Dia 1 ",
        "3ª série EM_PROVA PAULISTA_2º BI_EP_VENDAS_DIA 1",
        "PM_2º BI_EP_VENDAS_DIA 1",
        "OE - 2º ciclo - Médio - 3ª série - Dia 1",
    ],
]

import uuid
from fiscallizeon.exams.models import Exam, ExamTeacherSubject, ExamQuestion
from fiscallizeon.clients.models import ExamPrintConfig

def duplicate_instance_object(obj, TypeObject):
    instance = obj
    copy_object = TypeObject.objects.get(pk=instance.pk)
    copy_object.pk = uuid.uuid4()
    return copy_object

def copy_exam_teacher_subjects(original_exam, copy_exam):
    original_exam_teacher_subjects = original_exam.examteachersubject_set.using('default').all()
    for original_exam_teacher_subject in original_exam_teacher_subjects:
        copy_exam_teacher_subject = duplicate_instance_object(original_exam_teacher_subject, ExamTeacherSubject)
        copy_exam_teacher_subject.exam = copy_exam
        if already_exam_teacher_subject := copy_exam.examteachersubject_set.using('default').all().order_by('order').last():
            count_order_exam_teacher_subject = already_exam_teacher_subject.order
            copy_exam_teacher_subject.order = count_order_exam_teacher_subject + 1
        copy_exam_teacher_subject.save()
        copy_exam_questions(copy_exam, original_exam_teacher_subject, copy_exam_teacher_subject)

def copy_exam_questions(copy_exam, original_exam_teacher_subject, copy_exam_teacher_subject):
    original_exam_questions = original_exam_teacher_subject.examquestion_set.using('default').all()
    for original_exam_question in original_exam_questions:
        copy_exam_question = duplicate_instance_object(original_exam_question, ExamQuestion)
        copy_exam_question.exam = copy_exam
        copy_exam_question.exam_teacher_subject = copy_exam_teacher_subject
        copy_exam_question.save()

for d in data:
    exam_name_final = d[0].strip()
    copy_exam = None
    final_copy_exam = None
    if exam_name_1:= d[1].strip():
        if exam_1 := Exam.objects.filter(
                name=exam_name_1, coordinations__unity__client__name__icontains="seduc"
            ).first():
            copy_exam = duplicate_instance_object(exam_1, Exam)
            copy_exam.name = exam_name_final
            copy_exam.status = Exam.OPENED
            if exam_1.exam_print_config:
                copy_exam_print_config = ExamPrintConfig.objects.using('default').get(
                    pk=exam_1.exam_print_config.pk
                )
                copy_exam_print_config.pk = None
                copy_exam_print_config.name = f'Configuração {exam_name_final}'
                copy_exam_print_config.save()
                copy_exam.exam_print_config = copy_exam_print_config
            copy_exam.last_erp_sync = None
            copy_exam.save()
            final_copy_exam = Exam.objects.using('default').get(pk=copy_exam.pk)
            print(
                exam_name_final, 
                exam_1.name, 
                final_copy_exam.pk, 
                exam_1.coordinations.using('default').all()
            )
            final_copy_exam.coordinations.set(
                exam_1.coordinations.using('default').all()
            )
            final_copy_exam.save()
            copy_exam_teacher_subjects(exam_1, final_copy_exam)
        else:
            print(f'{exam_name_final}, 1-{exam_name_1}-')
    if exam_name_2:= d[2].strip():
        if exam_2 := Exam.objects.filter(
                name=exam_name_2, coordinations__unity__client__name__icontains="seduc"
            ).first():
            copy_exam_teacher_subjects(exam_2, final_copy_exam)
        else:
            print(f'{exam_name_final}, 2-{exam_name_2}-')
    if exam_name_3:= d[3].strip():
        if exam_3 := Exam.objects.filter(
                name=exam_name_3, coordinations__unity__client__name__icontains="seduc"
            ).first():
            copy_exam_teacher_subjects(exam_3, final_copy_exam)
        else:
            print(f'{exam_name_final}, 3-{exam_name_3}-')
    if exam_name_4:= d[4].strip():
        if exam_4 := Exam.objects.filter(
                name=exam_name_4, coordinations__unity__client__name__icontains="seduc"
            ).first():
            copy_exam_teacher_subjects(exam_4, final_copy_exam)
        else:
            print(f'{exam_name_final}, 4-{exam_name_4}-')