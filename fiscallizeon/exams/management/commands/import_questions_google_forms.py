import glob
import json

from django.core.management.base import BaseCommand

from fiscallizeon.clients.models import Client, SchoolCoordination
from fiscallizeon.classes.models import Grade
from fiscallizeon.questions.models import Question, QuestionOption


class Command(BaseCommand):
    help = 'Importa provas de um JSON de exportação do Google Forms'
    EXAMS_DIR = 'exams_lato/1ano'
    CLIENT_PK = 'f1a6a4e9-7b95-4045-b6dd-f720a17a14e1'
    GRADE = '1'

    def create_question(self, question_dict):
        if not question_dict:
            return

        if question_dict['type'] in ['TEXT', 'PARAGRAPH_TEXT', 'GRID']:
            category = Question.TEXTUAL
        elif question_dict['type'] in ['MULTIPLE_CHOICE', 'CHECKBOX']:
            category = Question.CHOICE
        elif question_dict['type'] in ['FILE_UPLOAD']:
            category = Question.FILE
        else:
            print('Questão ignorada: ', question_dict['type'])
            return
        
        if not question_dict['title']:
            print('Questão ignorada: enunciado vazio')
            return

        question, _ = Question.objects.get_or_create(
            enunciation=question_dict['title'].replace('por cento', '%'),
            category=category
        )

        if 'choices' in question_dict.keys():
            for index, choice in enumerate(question_dict['choices'], 1):
                QuestionOption.objects.get_or_create(
                    question=question,
                    text=choice['value'].replace('por cento', '%'),
                    is_correct=choice['isCorrect'],
                    index=index,
                )

        return question

    def handle(self, *args, **kwargs):
        client = Client.objects.get(pk=self.CLIENT_PK)
        coordinations = SchoolCoordination.objects.filter(unity__client=client, high_school=True)
        exams_files_list = glob.glob(self.EXAMS_DIR + '/**/*.json', recursive=True)
        grade = Grade.objects.get(name=self.GRADE, level=Grade.HIGHT_SCHOOL)

        for i, exam_path in enumerate(exams_files_list):
            print('Importando questoes do arquivo ', i+1)
            try:
                with open(exam_path, 'r') as f:
                    exam_json = json.loads(f.read())

                for question_item in exam_json['items']:
                    question = self.create_question(question_item)

                    if not question:                        
                        continue

                    question.grade = grade
                    question.save()

                    for coordination in coordinations:
                        question.coordinations.add(coordination)
       
            except Exception as e:
                import sys, os
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(exc_type, fname, exc_tb.tb_lineno)