import math

from django import template
from fiscallizeon.subjects.models import Subject
from fiscallizeon.exams.models import StatusQuestion, ExamTeacherSubject, ExamQuestion
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.questions.models import Question
from django.db.models import Q
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def get_correct_option_answer(question):
    if question.category == Question.CHOICE:
        alternatives = question.alternatives.all()
        correct_alternatives = []
        for i, alternative in enumerate(alternatives):
            if alternative.is_correct:
                correct_alternatives.append('abcdefghij'[i])
        if len(correct_alternatives) == alternatives.count():
            return "ANULADA"
        if len(correct_alternatives) > 0:
            return ', '.join(correct_alternatives)
        else:
            return '-'
    elif question.category == Question.SUM_QUESTION:
        correct_alternatives = question.alternatives.all().order_by('index')
        answer_value = sum([int(math.pow(2, i)) for i, a in enumerate(correct_alternatives) if a.is_correct])
        return f'({answer_value})'
    else:
        return '-'

@register.filter
def get_details(exam, user, exam_teacher_subject=None):
    exam_questions = exam.examquestion_set.filter(
        Q(exam_teacher_subject=exam_teacher_subject) if exam_teacher_subject else Q()
    ).distinct()
    
    common_query = Q(statusquestion__user=user) if not exam_teacher_subject else Q()
    
    count = exam_questions.count()
    count_reviewed_questions = exam_questions.filter(statusquestion__user=user).distinct().count()
    count_seen_questions = exam_questions.filter(Q(statusquestion__status=StatusQuestion.SEEN), common_query).distinct().count()
    count_approved_questions = exam_questions.filter(Q(statusquestion__status=StatusQuestion.APPROVED), common_query).distinct().count()
    count_reproved_questions = exam_questions.filter(Q(statusquestion__status=StatusQuestion.REPROVED), common_query).distinct().count()
    count_correction_pending_questions = exam_questions.filter(Q(statusquestion__status=StatusQuestion.CORRECTION_PENDING), common_query).distinct().count()
    count_question_choices = exam_questions.filter(question__category=Question.CHOICE).distinct().count()
    count_feedbacks = exam_questions.filter(question__category=Question.CHOICE, question__alternatives__is_correct=True).distinct().count()
    count_empty_feedbacks = count_question_choices - count_feedbacks
    
    count_peding_questions = exam_questions.filter(statusquestion__status=StatusQuestion.CORRECTION_PENDING, statusquestion__active=True).distinct().count()
    count_corrected_questions = exam_questions.filter(statusquestion__status=StatusQuestion.CORRECTED, statusquestion__active=True).distinct().count()
    count_opened_questions =  count - (count_approved_questions + count_reproved_questions + count_peding_questions + count_corrected_questions)

    return {
        "count": count,
        "count_total_questions": count,
        "count_reviewed_questions": count_reviewed_questions, 
        "count_seen_questions": count_seen_questions, 
        "count_approved_questions": count_approved_questions, 
        "count_reproved_questions": count_reproved_questions, 
        "count_correction_pending_questions": count_correction_pending_questions, 
        "count_question_choices": count_question_choices, 
        "count_feedbacks": count_feedbacks, 
        "count_empty_feedbacks": count_empty_feedbacks, 
        
        "count_peding_questions": count_peding_questions, 
        "count_corrected_questions": count_corrected_questions, 
        "count_opened_questions": count_opened_questions, 
    }

@register.filter
def get_exam_teacher_subject_details(exam_teacher_subject, user=None):
    
    exam_questions = exam_teacher_subject.examquestion_set.all().distinct()
    count_reviewed_questions = exam_questions.filter(Q(statusquestion__user=user) if user else Q()).distinct().count()
    
    return {
        "count_total_questions": exam_questions.count(),
        "count_reviewed_questions": count_reviewed_questions
    }

@register.filter
def get_exam_teacher_subject_pdf_review_details(exam_teacher_subject, user=None):
    
    exam_questions = exam_teacher_subject.examquestion_set.all().distinct()
    exams_questions_reviewed_pdf_counts = StatusQuestion.objects.filter(
        exam_question__in=exam_questions
        ).filter(
            Q(status=StatusQuestion.APPROVED) |
            Q(status=StatusQuestion.REPROVED) |
            Q(status=StatusQuestion.CORRECTION_PENDING) |
            Q(status=StatusQuestion.CORRECTED) |
            Q(status=StatusQuestion.ANNULLED) |
            Q(status=StatusQuestion.USE_LATER) |
            Q(status=StatusQuestion.DRAFT) |
            Q(status=StatusQuestion.RESPONSE)
    ).values('exam_question').distinct().count()
    
    return {
        "count_total_questions": exam_questions.count(),
        "count_reviewed_questions": exams_questions_reviewed_pdf_counts
    }
    
@register.filter
def get_exam_teacher_subjects(exam):
    exam_teacher_subjects = ExamTeacherSubject.objects.filter(exam=exam).order_by('order')
    return exam_teacher_subjects if exam_teacher_subjects.exists() else []

@register.filter
def get_exam_questions_availables(exam_teacher_subject, questions_categories: list = []):
    exam_questions_availables = exam_teacher_subject.examquestion_set.availables().filter(
        Q(question__category__in=questions_categories) if len(questions_categories) else Q()
    ).order_by('order')
    return exam_questions_availables if exam_questions_availables.exists() else []

@register.filter
def get_exam_abstract_subjects(exam):
    subjects = ExamQuestion.objects.filter(exam=exam).values("question__subject")
    return Subject.objects.filter(pk__in=subjects)

@register.filter
def get_exam_abstract_discursive_questions_subject(exam, subject):
    exam_questions = ExamQuestion.objects.filter(
        exam=exam, 
        question__category__in=[Question.TEXTUAL, Question.FILE],
        question__subject=subject
    ).order_by('order')
    return exam_questions if exam_questions.exists() else []
    
@register.filter
def get_content(custom_page, object=None):
    
    if type(object) == ApplicationStudent:
        return custom_page.get_content(application_student=object)
    
    if type(object) == SchoolClass:
        return custom_page.get_content(school_classe=object)
    
    return custom_page.get_content()    

@register.simple_tag
def get_content(custom_page, school_classe=None, application_student=None, application=None):
    return mark_safe(custom_page.get_content(school_classe=school_classe, application_student=application_student, application=application))

@register.filter
def get_foreign_language_index(subject_id, exam):
    
    if exam.is_abstract:
        return None
    else:
        subjects = list(exam.examteachersubject_set.filter(is_foreign_language=True).order_by('order').values_list('teacher_subject__subject__id', flat=True))
        
        if subject_id in subjects: 
            index = subjects.index(subject_id)
            return index
    
    return None

@register.filter
def get_teacher_obligation(user, level):
    return user.client_teacher_configuration(level=level)