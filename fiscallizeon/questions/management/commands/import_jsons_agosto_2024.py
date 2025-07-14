import os
import glob
import json

from django.core.management.base import BaseCommand
from django.db import transaction

from fiscallizeon.questions.models import Question, QuestionOption
from fiscallizeon.subjects.models import Topic, Subject
from fiscallizeon.classes.models import Grade


class Command(BaseCommand):
    help = 'Migra jsons de questões geradas em Agosto de 2024 para o banco público'
   
    BASE_DIR = 'tmp/persistence'

    def handle(self, *args, **kwargs):
        subjects_ids = {
            'Redação': '2a771795-d43a-47b6-bbc5-90e60f6082ce',
            'Espanhol': '3cfde1cf-5e9c-4461-b904-8d3854359f7c',
            'Linguagens, Códigos e suas Tecnologias': 'f109c14f-bd66-4241-bb61-06d0930b5c00',
            'Química': 'd172fe20-31f1-4b96-8128-16bea752ca84',
            'Filosofia': '90b3c199-77b4-43b7-b7e6-90e72b16a669',
            'Física': '5fe8484c-559e-4e75-9af6-4df9cf8847a1',
            'Ciências Humanas': '53ddfea3-6c2b-46bd-a1e2-d04f26fabee4',
            'Sociologia': 'dd970eef-c68a-4831-a144-f97901a0e615',
            'História': 'd8ffdbed-a6e5-4b9f-8f11-1eb2d944769e',
            'Artes': '0efcdaa7-6b9c-45f7-a7c5-db4d5598a792',
            'Biologia': 'fbbb4435-1df9-4812-ae29-34f3e6c78cfa',
            'Português': '29b82131-5ab7-4822-b5cc-4052cc1d5443',
            'Geografia': '02664d36-c9ce-4341-9722-101379960eda',
            'Inglês': '904d690c-6c74-4f92-833e-d736188a79a1',
            'Matemática': '50546b9b-b82e-4004-8f5a-f03eba7c14f2',
        }

        grade = Grade.objects.get(pk='e0ec150d-0e32-4c3f-928b-207bebcc3d22')
        dificulties = {
            1: Question.EASY, 
            2: Question.MEDIUM, 
            3: Question.HARD
        }

        for json_path in glob.glob(self.BASE_DIR + '/cosseno/**/*.json', recursive=True):
            filename = os.path.basename(json_path)

            if os.path.isfile(self.BASE_DIR + '/imported/' + filename):
                print("Questão já importada, ignorando...")
                continue

            with open(json_path, 'r') as file:
                question_json = json.loads(file.read())
                subject = Subject.objects.filter(pk=subjects_ids[question_json['subject']]).first()

                if not subject:
                    print(f'Disciplina {question_json["subject"]} não encontrada')
                    continue
                
                with transaction.atomic():
                    ignore_question = False
                    savepoint = transaction.savepoint()
                    question = Question.objects.create(
                        is_public=True,
                        subject=subject,
                        grade=grade,
                        board=question_json['board'],
                        institution=question_json['board'],
                        elaboration_year=question_json['elaboration_year'],
                        level=dificulties.get(question_json['level'], Question.UNDEFINED),
                        enunciation=question_json['enunciation'],
                        category=question_json['category'],
                    )

                    if question.category == Question.CHOICE:
                        try:
                            correct_index = 'abcdefghij'.index(question_json['answer'][0].lower())
                        except Exception as e:
                            transaction.savepoint_rollback(savepoint)
                            continue

                        for index, alternative in enumerate(question_json['alternatives']):
                            if not alternative:
                                ignore_question = True
                                break

                            QuestionOption.objects.create(
                                question=question,
                                text=alternative,
                                is_correct=correct_index==index,
                                index=index,
                            )

                    if ignore_question:
                        transaction.savepoint_rollback(savepoint)
                        print(f"Arquivo {filename} ignorado.")
                        continue
                    else:
                        transaction.savepoint_commit(savepoint)

                for topic_name in question_json['topics']:
                    topic, _ = Topic.objects.get_or_create(
                        grade=grade,
                        subject=subject,
                        name=topic_name.strip(),
                        client__isnull=True,
                    )
                    question.topics.add(topic)

                with open(self.BASE_DIR + '/imported/' + filename, 'w') as file:
                    file.write(str(question.pk))

                print(f'Questão {question.pk} criada com sucesso')
