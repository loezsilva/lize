import re
import json

from draftjs_exporter.html import HTML
from draftjs_exporter.constants import BLOCK_TYPES, ENTITY_TYPES
from draftjs_exporter.defaults import BLOCK_MAP, STYLE_MAP
from draftjs_exporter.dom import DOM

from django.core.management.base import BaseCommand

from fiscallizeon.questions.models import Question, QuestionOption
from fiscallizeon.subjects.models import KnowledgeArea, Subject, Topic
from fiscallizeon.exams.models import Exam
from fiscallizeon.clients.models import SchoolCoordination

class Command(BaseCommand):
    help = 'Importa lista de questões do Go Formative para o banco de questões'

    def add_arguments(self, parser):
        parser.add_argument('coordination_id', nargs=1, type=str)

    def formula(props):
        content = props.get("content").replace('\\', '\\\\')
        content = f'\\\({content}\\\)' if props.get("content") else ''
        return DOM.create_element('span', {}, content)

    config = {
        'block_map': dict(BLOCK_MAP, **{
            BLOCK_TYPES.HEADER_TWO: 'h2',
            BLOCK_TYPES.HEADER_THREE: {'element': 'h3', 'props': {'class': 'u-text-center'}},
            BLOCK_TYPES.UNORDERED_LIST_ITEM: {
                'element': 'li',
                'wrapper': 'ul',
                'wrapper_props': {'class': 'bullet-list'},
            },
        }),
        'style_map': dict(STYLE_MAP, **{
            'KBD': 'kbd',
            'HIGHLIGHT': {'element': 'strong', 'props': {'style': {'textDecoration': 'underline'}}},
        }),
        'entity_decorators': {
            'MATH': 'text',
            'SUPERSCRIPT': "sup",
            'TEX': formula,
            ENTITY_TYPES.IMAGE: "image",
            ENTITY_TYPES.LINK: "link",
            ENTITY_TYPES.EMBED: None,
        },
    }

    def handle(self, *args, **kwargs):
        exporter = HTML(self.config)
        count = 0

        coordination = SchoolCoordination.objects.get(pk=kwargs['coordination_id'][0])
        
        exam, _ = Exam.objects.get_or_create(
            coordination=coordination,
            name='Simulado Escalada - 1º dia'
        )

        with open('questions.json', 'r') as questions_file:
            questions = json.loads(questions_file.read())['data']['formative']['items']

        for question in questions:
            if question['type'] == 'question':
                count += 1

                if 1 <= count <= 50:
                    knowledge_area, _ = KnowledgeArea.objects.get_or_create(
                        name='Linguagens, códigos e suas tecnologias'
                    )
                else:
                    knowledge_area, _ = KnowledgeArea.objects.get_or_create(
                        name='Ciências humanas e suas tecnologias'
                    )

                subject, _ = Subject.objects.get_or_create(
                    name='Geral',
                    knowledge_area=knowledge_area
                )
                
                topic, _ = Topic.objects.get_or_create(
                    name='Geral',
                    subject=subject
                )

                try:
                    question_text = json.loads(question['text'])
                    question_text = exporter.render(question_text)
                except Exception as e:
                    question_text = question['text']
                
                question_db, _ = Question.objects.get_or_create(
                    topic=topic,
                    coordination=coordination,
                    enunciation=question_text
                )

                details = question['details']
                answer_index = details['choices'].index(details['correctAnswers'][0])

                for index, choice in enumerate(details['choiceLabels']):
                    try:
                        alternative_text = json.loads(choice)
                        alternative_text = exporter.render(alternative_text)
                    except Exception as e:
                        alternative_text = choice

                    is_correct = answer_index == index

                    alternative, _ = QuestionOption.objects.get_or_create(
                        question=question_db,
                        text=alternative_text,
                        is_correct=is_correct,
                    )

                exam.questions.add(question_db)