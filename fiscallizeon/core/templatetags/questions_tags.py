from django import template
from decimal import Decimal
from fiscallizeon.answers.models import FileAnswer, OptionAnswer, TextualAnswer, SumAnswerQuestionOption
from django.db.models import Sum, Count, Q
from fiscallizeon.bncc.models import Abiliity, Competence
from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.questions.models import Question
from fiscallizeon.subjects.models import Topic
from django.template.defaultfilters import safe

register = template.Library()

@register.simple_tag
def tag_get_alternative_percentage(alternative, exam, objetive_answers_count, coordinations, q_applications=None, q_unities=None, q_classes=None):
    if alternative.question.category == Question.CHOICE:
        answers = OptionAnswer.objects.filter(
            Q(question_option=alternative),
            Q(status=OptionAnswer.ACTIVE),
            Q(question_option__question__exams=exam),
            Q(student_application__student__classes__coordination__in=coordinations),
            Q(student_application__student__classes__school_year=exam.application_set.first().date.year),
            Q(student_application__application__in=q_applications) if q_applications else Q(),
            Q(student_application__student__classes__coordination__unity__in=q_unities) if q_unities and not q_classes else Q(),
            Q(student_application__student__classes__in=q_classes) if q_classes else Q(),
        ).distinct()
        return (answers.count() / int(objetive_answers_count) * 100) if int(objetive_answers_count) > 0 else 0
    
    answers = SumAnswerQuestionOption.objects.filter(
        Q(checked=True),
        Q(question_option=alternative),
        Q(question_option__question__exams=exam),
        Q(sum_answer__student_application__student__classes__coordination__in=coordinations),
        Q(sum_answer__student_application__student__classes__school_year=exam.application_set.first().date.year),
        Q(sum_answer__student_application__application__in=q_applications) if q_applications else Q(),
        Q(sum_answer__student_application__student__classes__coordination__unity__in=q_unities) if q_unities and not q_classes else Q(),
        Q(sum_answer__student_application__student__classes__in=q_classes) if q_classes else Q(),
    ).distinct()

    return (answers.count() / int(objetive_answers_count) * 100) if int(objetive_answers_count) > 0 else 0

@register.simple_tag
def tag_get_discursive_percentage(question, exam, discursive_answers_count, coordinations, q_applications=None, q_unities=None, q_classes=None):
    summary = {
        0: 0,
        25: 0,
        50: 0,
        75: 0,
        100: 0,
    }
    if question == Question.CHOICE:
        return summary
    
    exam_question = ExamQuestion.objects.get(question=question, exam=exam)
    
    if discursive_answers_count:
        if question.category == Question.TEXTUAL:
            answers = TextualAnswer.objects.filter(
                Q(question=question),
                Q(content__isnull=False),
                Q(student_application__student__classes__school_year=exam.application_set.first().date.year),
                Q(student_application__application__in=q_applications) if q_applications else Q(),
                Q(student_application__student__classes__coordination__in=coordinations),
                Q(student_application__student__classes__coordination__unity__in=q_unities) if q_unities and not q_classes else Q(),
                Q(student_application__student__classes__in=q_classes) if q_classes else Q(),
            ).annotate(
                total_0=Count('pk', filter=Q(teacher_grade=0)),
                total_25=Count('pk', filter=Q(teacher_grade__gt=0, teacher_grade__lt=(exam_question.weight * Decimal(0.50)))),
                total_50=Count('pk', filter=Q(teacher_grade__gte=(exam_question.weight * Decimal(0.5)), teacher_grade__lt=(exam_question.weight * Decimal(0.75)))),
                total_75=Count('pk', filter=Q(teacher_grade__gte=(exam_question.weight * Decimal(0.75)), teacher_grade__lt=exam_question.weight)),
                total_100=Count('pk', filter=Q(teacher_grade__gte=exam_question.weight)),
            )
                        
        else:
            answers = FileAnswer.objects.filter(
                Q(question=question),
                Q(arquivo__isnull=False),
                Q(student_application__student__classes__coordination__in=coordinations),
                Q(student_application__student__classes__school_year=exam.application_set.first().date.year),
                Q(student_application__application__in=q_applications) if q_applications else Q(),
                Q(student_application__student__classes__coordination__unity__in=q_unities) if q_unities and not q_classes else Q(),
                Q(student_application__student__classes__in=q_classes) if q_classes else Q(),
            ).annotate(
                total_0=Count('pk', filter=Q(teacher_grade=0)),
                total_25=Count('pk', filter=Q(teacher_grade__gt=0, teacher_grade__lt=(exam_question.weight * Decimal(0.50)))),
                total_50=Count('pk', filter=Q(teacher_grade__gte=(exam_question.weight * Decimal(0.5)), teacher_grade__lt=(exam_question.weight * Decimal(0.75)))),
                total_75=Count('pk', filter=Q(teacher_grade__gte=(exam_question.weight * Decimal(0.75)), teacher_grade__lt=exam_question.weight)),
                total_100=Count('pk', filter=Q(teacher_grade__gte=exam_question.weight)),
            )
        
        count_answers = answers.count()
        
        summary[0] = answers.aggregate(Sum('total_0')).get('total_0__sum') or 0
        summary[25] = answers.aggregate(Sum('total_25')).get('total_25__sum') or 0
        summary[50] = answers.aggregate(Sum('total_50')).get('total_50__sum') or 0
        summary[75] = answers.aggregate(Sum('total_75')).get('total_75__sum') or 0
        summary[100] = answers.aggregate(Sum('total_100')).get('total_100__sum') or 0
        
        # Perse to percent values
        summary[0] = (summary[0] / count_answers) * 100 if summary[0] and count_answers else 0
        summary[25] = (summary[25] / count_answers) * 100 if summary[25] and count_answers else 0
        summary[50] = (summary[50] / count_answers) * 100 if summary[50] and count_answers else 0
        summary[75] = (summary[75] / count_answers) * 100 if summary[75] and count_answers else 0
        summary[100] = (summary[100] / count_answers) * 100 if summary[100] and count_answers else 0
    
    return summary

@register.filter
def get_alternative_percentages(alternative, exam):
    answers = OptionAnswer.objects.filter(
        status=OptionAnswer.ACTIVE,
        question_option__question__exams=exam,
        question_option=alternative
    )
    return answers.count()

@register.filter
def get_questions(obj, exam):
    obj_class = type(obj)
    questions = exam.questions.availables(exam)

    if(obj_class == Topic):
        questions = questions.filter(topics=obj)    
    elif obj_class == Abiliity:
        questions = questions.filter(abilities=obj)
    elif obj_class == Competence:
        questions = questions.filter(competences=obj)
        
    return [str(question.id) for question in questions] if questions else []


@register.simple_tag
def get_ability_percentages(obj, exam, user):
    
    coordinations = user.get_coordinations_cache()
    
    applications_student = list(
        exam.get_application_students_started(
            coordinations=coordinations
        ).values_list('id', flat=True)
    )
    
    details = exam.get_applications_student_bnccs_details(
        applications_student=applications_student,
        bncc_id=obj.id,
        type=obj.__class__.__name__
    )

    corrects = details['corrects']
    incorrects = details['incorrects']
    total_answers = details['total_answers']
    performance = (corrects / total_answers) * 100 if total_answers else 0

    return safe({
        "total_correct_objetives": corrects,
        "total_incorrect_objetives": incorrects,
        "total_answers": total_answers,
        "percentage_of_hits": performance,
        "total_questions": details['total_questions'],
    })
    
@register.filter
def get_subject_header(subject_id, subject_indexs):
    header = list(filter(lambda index: index.get("subject_id") == subject_id, subject_indexs))
    return header[0].get('index')

@register.filter
def check_can_be_updated(question, user):
    return question.can_be_updated(user=user)

@register.filter
def check_can_be_updated_with_reason(question, user):
    return question.can_be_updated_with_reason(user=user)

@register.filter
def get_instance(question_id):
    return Question.objects.get(id=question_id)