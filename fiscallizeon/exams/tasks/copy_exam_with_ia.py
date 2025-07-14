from celery import states
import uuid
from fiscallizeon.celery import app
from fiscallizeon.accounts.models import User
from fiscallizeon.questions.models import Question, QuestionOption
from fiscallizeon.exams.models import ExamQuestion, ExamTeacherSubject, Exam
from django.db import transaction
from fiscallizeon.ai.openai.questions import create_adapted_question


def create_prompt(exam_question, exam_question_json, reduced_text_alternatives, reduced_quantity_alternatives, reduced_enunciation):
    prompt = f"Enunciado original: '{exam_question.question.enunciation}'. "

    prompt += "Alternativas originais: "
    for alternative_index, alternative_pk in enumerate(exam_question_json['alternatives'], 1):
        original_alternative = QuestionOption.objects.get(pk=alternative_pk)
        if original_alternative.is_correct:
            prompt += f"Alternativa {alternative_index}: '{original_alternative.text}' (Correta). "
        else:
            prompt += f"Alternativa {alternative_index}: '{original_alternative.text}'. "
    
    if reduced_enunciation:
        prompt += " -  Reduza o enunciado original da questão sem remover as imagens, caso existam, simplificando o conteúdo sem alterar o significado."

    if reduced_quantity_alternatives:
        prompt += " - Reduza uma alternativa, mantendo uma distribuição balanceada entre as corretas e incorretas."

    if reduced_text_alternatives:
        prompt += " - Caso existam alternativas reduza de forma significativa texto das alternativas sem remover as imagens, simplificando o conteúdo sem alterar o significado."
    
    return prompt

def duplicate_question(question_id):
        original_question = Question.objects.get(pk=question_id)
        copy_question = Question.objects.get(pk=question_id)
        copy_question.pk = uuid.uuid4()
        copy_question.source_question = original_question
        copy_question.is_essay = original_question.is_essay  
        copy_question.save()

        copy_question.coordinations.set(original_question.coordinations.all())
        copy_question.topics.set(original_question.topics.all())
        copy_question.abilities.set(original_question.abilities.all())
        copy_question.competences.set(original_question.competences.all())
        copy_question.base_texts.set(original_question.base_texts.all())

        return copy_question

@app.task(bind=True, max_retries=1)
def copy_exam_with_ia(self, user_pk, copy_exam_pk, original_exam_pk, exam_json_copy,
                    reduced_text_alternatives, reduced_enunciation, reduced_quantity_alternatives):
    self.update_state(state=states.STARTED)

    original_exam = Exam.objects.get(pk=original_exam_pk)
    user = User.objects.get(pk=user_pk)
    copy_exam = Exam.objects.using('default').get(pk=copy_exam_pk)
    copy_exam.copy_exam_with_ia_status = Exam.COPYING
    copy_exam.save()
    
    try:
        with transaction.atomic():

            for index, exam_teacher_subject_json in enumerate(exam_json_copy['exam_teacher_subjects']):
                exam_teacher_subject = ExamTeacherSubject.objects.get(
                    pk=exam_teacher_subject_json['pk'],
                )

                exam_teacher_subject.pk = None
                exam_teacher_subject.exam = copy_exam
                exam_teacher_subject.order = index
                exam_teacher_subject.save(skip_hooks=True)

                for exam_question_index, exam_question_json in enumerate(exam_teacher_subject_json['exam_questions']):
                    exam_question = ExamQuestion.objects.get(
                        pk=exam_question_json['pk']
                    )
                    exam_question.pk = None
                    exam_question.exam = copy_exam
                    exam_question.order = exam_question_index
                    exam_question.exam_teacher_subject = exam_teacher_subject
            
                    prompt = create_prompt(
                        exam_question,
                        exam_question_json,
                        reduced_text_alternatives,
                        reduced_quantity_alternatives,
                        reduced_enunciation
                    )
                    new_question = create_adapted_question(user, prompt)
                    copy_question = duplicate_question(exam_question.question.pk)
                    copy_question.enunciation = new_question.get('enunciation', copy_question.enunciation)
                    copy_question.created_with_ai = True
                    copy_question.save()

                    if 'alternatives' in new_question:
                        for alternative_data in new_question['alternatives']:
                            QuestionOption.objects.create(
                                pk=uuid.uuid4(), 
                                question=copy_question, 
                                text=alternative_data.get('text', ''),
                                is_correct=alternative_data.get('is_correct', False) 
                            )
                    exam_question.question = copy_question
                    exam_question.save()
            
            self.update_state(state=states.SUCCESS)
            original_exam.copy_exam_with_ia_count += 1
            original_exam.save()
            copy_exam.copy_exam_with_ia_status = Exam.FINISHED
            copy_exam.save()
         

    except Exception as e:
        print(f"Error in transaction: {e}")
     
        copy_exam.copy_exam_with_ia_status = Exam.ERROR
        copy_exam.save()
        self.update_state(state=states.FAILURE)
        raise
