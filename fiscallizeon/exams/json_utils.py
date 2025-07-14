"""
Este módulo implementa métodos para geração de JSONs relacionados às provas
"""
import uuid

from django.db.models import Case, When

from fiscallizeon.exams.models import ExamTeacherSubject, ExamQuestion
from fiscallizeon.questions.models import Question

def _get_exam_questions_json(exam_teacher_subject):
    questions_list = []
    for exam_question in exam_teacher_subject.examquestion_set.availables():
        questions_list.append({
            "pk": str(exam_question.pk),
            "category": exam_question.question.category,
            "number_is_hidden": exam_question.question.number_is_hidden,
            "base_texts": [
                str(base_text['pk'])
                for base_text in exam_question.question.base_texts.all().order_by(
                    'created_at'
                ).values('pk')
            ],
            "block": None, #TODO: Alterar quando o modelo de ExamQuestion tiver o campo block
            "alternatives": [
                str(alternative.pk)
                for alternative in exam_question.question.alternatives.all().order_by(
                    'index', 'created_at'
                )
            ],
        })
    
    return questions_list

def get_exam_base_json(exam):
    result_json = {"exam_teacher_subjects": []}
    exam_teacher_subjects = ExamTeacherSubject.objects.filter(exam=exam)
    for exam_teacher_subject in exam_teacher_subjects:
        result_json["exam_teacher_subjects"].append(
            {
                "pk": str(exam_teacher_subject.pk),
                "exam_questions": _get_exam_questions_json(exam_teacher_subject),
            }
        )
    return result_json

def convert_json_to_exam_questions_list(exam_json):
    questions_list = []
    for exam_teacher_subject in exam_json['exam_teacher_subjects']:
        for exam_question in exam_teacher_subject['exam_questions']:

            if exam_question['number_is_hidden']:
                continue

            questions_list.append(
                {
                    "pk": exam_question['pk'],
                    "alternatives": [
                        alternative_pk
                        for alternative_pk in exam_question['alternatives']
                    ],
                }
            )

    return questions_list

def convert_json_to_questions_list(exam_json):
    questions_list = []
    exam_questions_list = []

    for exam_teacher_subject in exam_json['exam_teacher_subjects']:
        exam_questions_list.extend([
            {'pk': eq['pk'], 'alternatives': eq['alternatives']} 
            for eq in exam_teacher_subject['exam_questions']
        ])
    
    exam_questions_pks = [eq['pk'] for eq in exam_questions_list]
    preserved = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(exam_questions_pks)])
    exam_questions = ExamQuestion.objects.filter(pk__in=exam_questions_pks).order_by(preserved)
    for exam_question in exam_questions:
        questions_list.append(
            {
                "pk": str(exam_question.question_id),
                "alternatives": next((eq for eq in exam_questions_list if eq['pk'] == str(exam_question.pk)), None)['alternatives'],
            }
        )

    return questions_list

def convert_json_to_choice_exam_questions_list(exam_json):
    questions_list = []
    for exam_teacher_subject in exam_json['exam_teacher_subjects']:
        for exam_question in exam_teacher_subject['exam_questions']:
            
            if exam_question['category'] != Question.CHOICE:
                continue

            if exam_question['number_is_hidden']:
                continue

            questions_list.append(
                {
                    "pk": exam_question['pk'],
                    "alternatives": [
                        alternative_pk
                        for alternative_pk in exam_question['alternatives']
                    ],
                }
            )

    return questions_list

def convert_json_to_textual_exam_questions_list(exam_json):
    questions_list = []
    for exam_teacher_subject in exam_json['exam_teacher_subjects']:
        for exam_question in exam_teacher_subject['exam_questions']:
            
            if exam_question['category'] not in [Question.TEXTUAL, Question.FILE]:
                continue

            if exam_question['number_is_hidden']:
                continue

            questions_list.append({
                "pk": exam_question['pk'],
            })

    return questions_list

def convert_json_to_sum_exam_questions_list(exam_json):
    questions_list = []
    for exam_teacher_subject in exam_json['exam_teacher_subjects']:
        for exam_question in exam_teacher_subject['exam_questions']:
            
            if exam_question['category'] != Question.SUM_QUESTION:
                continue

            if exam_question['number_is_hidden']:
                continue

            questions_list.append({
                "pk": exam_question['pk'],
            })

    return questions_list

def convert_json_to_choice_questions_list(exam_json):
    questions_list = []
    for exam_teacher_subject in exam_json['exam_teacher_subjects']:
        exam_questions_ids = [exam_question['pk'] for exam_question in exam_teacher_subject['exam_questions']]
        exam_questions = ExamQuestion.objects.in_bulk(exam_questions_ids)

        for exam_question in exam_teacher_subject['exam_questions']:
            questions_list.append({
                "pk": exam_questions[uuid.UUID(exam_question['pk'])].question_id,
                "alternatives": exam_question['alternatives'],
            })

    return questions_list