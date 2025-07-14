import os
import requests
import re
from celery import states
from django.db import transaction
from django.conf import settings

from fiscallizeon.celery import app
from fiscallizeon.accounts.models import User
from fiscallizeon.subjects.models import Topic
from fiscallizeon.bncc.models import Competence, Abiliity
from fiscallizeon.questions.models import Question, QuestionOption
from fiscallizeon.exams.models import ExamQuestion, ExamTeacherSubject
from fiscallizeon.ai.openai.questions import create_new_questions_for_item_request


def generate_prompt(current_data, exam_teacher_subject, competences, abilities,topics, level_number):    
    
    level_name = dict(Question.LEVEL_CHOICES).get(level_number, "Indefinido")
    competence_text = ', '.join(comp.text for comp in competences) if competences else 'Nenhuma competência'
    ability_text = ', '.join(abi.text for abi in abilities) if abilities else 'Nenhuma habilidade'
    topic_text = ', '.join(topic.name for topic in topics) if topics else 'Nenhum tópico'

    prompt = (
        f"{current_data['prompt']}. As questões geradas devem ser para a disciplina "
        f"{exam_teacher_subject.teacher_subject.subject.name}, destinadas aos alunos do/da "
        f"{exam_teacher_subject.grade.full_name}. Certifique-se de que as perguntas são "
        f"adequadas para o nível educacional dos alunos e abordem os tópicos principais da disciplina. "
        f"Competências: {competence_text}, Habilidades: {ability_text}, Tópicos: {topic_text}, Nível da questão: {level_name}."
    )

    return prompt

def get_filtered_objects_and_level(current_data):

    competences_ids = current_data.get('competences', [])
    abilities_ids = current_data.get('abilities', [])
    topics_ids = current_data.get('topics', [])
    level = current_data.get('level', 3)

    competences = Competence.objects.filter(pk__in=[pk for pk in competences_ids if pk])
    abilities = Abiliity.objects.filter(pk__in=[pk for pk in abilities_ids if pk])
    topics = Topic.objects.filter(pk__in=[pk for pk in topics_ids if pk])
    level = int(level) if level.isdigit() else 3
    
    return competences, abilities, topics,level

def extract_data_from_prompt(user_prompt):
    pattern = re.compile(
        r'level:(.*?)&&abilities:(.*?)&&competences:(.*?)&&topic:(.*?)&&image:(.*?)&&prompt:(.*?)(@@@|$)',
    )

    matches = pattern.findall(user_prompt)    
    data_list = []

    for match in matches:
        data_list.append({
            'level': match[0].strip(),
            'abilities': match[1].strip().split('###') if match[1] else [],
            'competences': match[2].strip().split('###') if match[2] else [],
            'topics': match[3].strip().split('###') if match[3] else [],
            'image': match[4].strip(),
            'prompt': match[5].strip()
        })

    return data_list

@app.task(bind=True, max_retries=1)
def create_exam_question_ia(self, user_pk, exam_pk, exam_teacher_subjct_pk, user_prompt, quantity):
    exam_teacher_subject = None
    try:
        user = User.objects.get(pk=user_pk)
        exam_teacher_subject = ExamTeacherSubject.objects.get(pk=exam_teacher_subjct_pk)
        user_coordinations = user.get_coordinations()
        prompts_data = extract_data_from_prompt(user_prompt)

        if len(prompts_data) < quantity:
            repeats = quantity // len(prompts_data)
            remainder = quantity % len(prompts_data)
            prompts_data = prompts_data * repeats + prompts_data[:remainder]
        
        with transaction.atomic():
            for order in range(1, quantity + 1):
                current_data = prompts_data[order - 1]

                support_image_url = current_data.get('image')

                competences, abilities, topics,level = get_filtered_objects_and_level(current_data)

                prompt = generate_prompt(current_data, exam_teacher_subject, competences, abilities, topics, level)
            
                gpt_question = create_new_questions_for_item_request(user, prompt, support_image_url)

                if not gpt_question:
                    raise ValueError("GPT question creation failed, returned None.")

                base_text = gpt_question.get('base_text', '')
                enunciation = gpt_question.get('enunciation', '')

                if support_image_url:
                    image_tag = (
                        f'<div style="text-align: center;">'
                        f'<img src="{support_image_url}" alt="Support Image" style="width: 80%; height: auto;"/>'
                        f'</div>'
                    )
                    enunciation = f"{image_tag}<br><br>{base_text}<br><br>{enunciation}"
                else:
                    enunciation = f"{base_text}<br><br>{enunciation}"

                question = Question.objects.create(
                    subject=exam_teacher_subject.teacher_subject.subject,
                    grade=exam_teacher_subject.grade,
                    enunciation=enunciation.replace("\n", ""),
                    commented_awnser=gpt_question.get('commented_answer'),
                    created_by=exam_teacher_subject.teacher_subject.teacher.user,
                    level=int(level),
                    is_essay=False
                )

                if abilities.exists():
                    question.abilities.set(abilities)
                if competences.exists():
                    question.competences.set(competences)
                if topics.exists():
                    question.topics.set(topics)

                question.coordinations.set(user_coordinations)

                for alt in gpt_question.get('alternatives', []):
                    QuestionOption.objects.create(
                        question=question,
                        text=alt['text'].replace("\\n", ""),
                        is_correct=alt['is_correct']
                    )

                exam_question = ExamQuestion.objects.create(
                    question=question,
                    exam_id=exam_pk,
                    exam_teacher_subject=exam_teacher_subject,
                    order=order
                )
        
            transaction.on_commit(lambda: exam_question.send_email_to_coordination_after_AI_generates_questions())
            exam_teacher_subject.question_generation_status_with_ai=ExamTeacherSubject.FINISHED
            exam_teacher_subject.save()

    except Exception as e:
        print(f"Error in transaction: {e}")

    finally:
        if exam_teacher_subject and exam_teacher_subject.question_generation_status_with_ai != ExamTeacherSubject.FINISHED:
            exam_teacher_subject.has_error_create_exam_question_ia = True
            exam_teacher_subject.question_generation_status_with_ai = ExamTeacherSubject.ERROR
            exam_teacher_subject.save()
