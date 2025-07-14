import re
import glob
import json
import unicodedata
import html
# from html.parser import HTMLParser

from django.core.management.base import BaseCommand

from fiscallizeon.subjects.models import KnowledgeArea, Subject, Topic
from fiscallizeon.questions.models import Question, QuestionOption


class Command(BaseCommand):
    help = 'Corrige problema de questões importadas sem assunto'
    QUESTIONS_DIR = './questions'

    def get_knowledge_area(self, name):
        area_names = {
            'CN': 'Ciências da Natureza e suas Tecnologias - Ensino Médio',
            'CH': 'Ciências Humanas e Sociais Aplicadas - Ensino Médio',
            'MT': 'Matemática e suas Tecnologias - Ensino Médio',
            'LC': 'Linguagens e suas Tecnologias - Ensino Médio',
        }
        try:
            return KnowledgeArea.objects.using('default').get(name=area_names[name])
        except:
            raise Exception(f'{area_names[name]} não existe')

    def get_subject(self, knowledge_area, name):
        subject_names = {
            'ATU': 'Atualidades',
            'FIL': 'Filosofia',
            'GEO': 'Geografia',
            'HIS': 'História',
            'SOC': 'Sociologia',
            'BIO': 'Biologia',
            'FIS': 'Física',
            'QUI': 'Química',
            'ART': 'Artes',
            'ESP': 'Língua Espanhola',
            'ING': 'Língua Inglesa',
            'LIT': 'Literatura',
            'POR': 'Língua Portuguesa',
            'RED': 'Redação',
            'MAT': 'Matemática',
            'MAT-BAS': 'Matemática Básica' #Criar antes
        }

        subject, _ = Subject.objects.using('default').get_or_create(
            knowledge_area=knowledge_area,
            name=subject_names.get(name, 'Geral')
        )

        return subject

    def handle(self, *args, **kwargs):
        question_files_list = glob.glob(self.QUESTIONS_DIR + '/**/*.json', recursive=True)

        for i, question_path in enumerate(question_files_list):
            with open(question_path, 'r') as f:
                question_json = json.loads(f.read())

            if not question_json.get('database_id', None):
                print('Questão não importada')
                continue

            knowledge_area = self.get_knowledge_area(question_json['area'])
            subject = self.get_subject(knowledge_area, question_json['dis'])

            topic_name = unicodedata.normalize("NFKD", question_json.get(
                'au_nome', ''
            )).replace('\n', '').replace('\r', '').replace('\t', '')
            topic = None

            if topic_name:
                print(f"Trabalhando no tópico {topic_name}")
                topic, _ = Topic.objects.using('default').get_or_create(
                    subject=subject,
                    name=topic_name,
                )        
            
            question = Question.objects.using('default').get(
                pk=question_json.get('database_id')
            )

            question.topics.add(topic)
            print(f'{i} - Questão {question_json["database_id"]} ajustada')