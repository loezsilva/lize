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
    help = 'Importa lista de questões em JSON oriundas da API pública'
    QUESTIONS_DIR = './questions'

    def get_knowledge_area(self, name):
        area_names = {
            'CN': 'Ciências da Natureza e suas Tecnologias - Ensino Médio',
            'CH': 'Ciências Humanas e Sociais Aplicadas - Ensino Médio',
            'MT': 'Matemática e suas Tecnologias - Ensino Médio',
            'LC': 'Linguagens e suas Tecnologias - Ensino Médio',
        }
        try:
            return KnowledgeArea.objects.get(name=area_names[name])
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

        subject, _ = Subject.objects.get_or_create(
            knowledge_area=knowledge_area,
            name=subject_names.get(name, 'Geral')
        )

        return subject

    def get_question_level(self, level):
        level = unicodedata.normalize("NFKD", level).replace('\n', '').replace('\r', '').replace('\t', '')
        
        levels = {
            'F': Question.EASY,
            'M': Question.MEDIUM,
            'D': Question.HARD,
        }
        
        return levels.get(level[0], Question.UNDEFINED)

    def handle(self, *args, **kwargs):
        question_files_list = glob.glob(self.QUESTIONS_DIR + '/**/*.json', recursive=True)

        for i, question_path in enumerate(question_files_list):
            with open(question_path, 'r') as f:
                question_json = json.loads(f.read())

            if question_json.get('database_id', None):
                print(f'{i} - Questão {question_json["id_comp"]} já importada')
                continue

            knowledge_area = self.get_knowledge_area(question_json['area'])
            subject = self.get_subject(knowledge_area, question_json['dis'])

            topic_name = unicodedata.normalize("NFKD", question_json.get('au_nome', '')).replace('\n', '').replace('\r', '').replace('\t', '')
            topic = None

            if topic_name:
                topic, _ = Topic.objects.get_or_create(
                    subject=subject,
                    name=topic_name,
                )
        
            # parser = HTMLParser()
            parser = html

            enunciation = parser.unescape(question_json.get('enum'))
            adjusted_enunciation = enunciation.replace(
                '/media/questions/images/',
                'https://fiscallizeremote.nyc3.digitaloceanspaces.com/fiscallizeremote/media/questoes-publicas/'
            )

            question = Question.objects.create(
                subject=subject,
                board=question_json.get('banca', None),
                institution=question_json.get('orgao', None),
                is_public=True,
                level=self.get_question_level(question_json.get('nivel', None)),
                elaboration_year=question_json.get('ano', None),
                enunciation=adjusted_enunciation,
            )

            question.topics.add(topic)

            for index, option_json in enumerate(question_json['itens'], 1):
                raw_alternative = parser.unescape(option_json['item_txt'])
                alternative_text = re.sub(r'<b>\s*\w\)\s*</b>', r'', raw_alternative, count=1)
                alternative_text = alternative_text.replace(
                        '/media/questions/images/',
                        'https://fiscallizeremote.nyc3.digitaloceanspaces.com/fiscallizeremote/media/questoes-publicas/'
                    )

                QuestionOption.objects.create(
                    question=question,
                    text=alternative_text,
                    is_correct=option_json.get('item_certo', '0') == '1',
                    index=index,
                )


            with open(question_path, 'w') as question_file:
                question_json['database_id'] = str(question.pk)
                json.dump(question_json, question_file)

            print(f'{i} - Questão {question_json["id_comp"]} importada')