import os
import csv
import shutil
import requests

from django.core.management.base import BaseCommand

from datetime import datetime
from fiscallizeon.questions.models import Question
from fiscallizeon.subjects.models import Topic, MainTopic, Theme

class Command(BaseCommand):
    # help = 'Importa alunos de CSV'
    
    
    def add_arguments(self, parser):
        pass
        
    def csv_to_dict(self, csv_file):    
        data = []  
        
        with requests.get(csv_file, stream=True) as r:
            
            tmp_file = os.path.join("/tmp/students.csv")
            
            with open(tmp_file, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
            
            with open(tmp_file, 'r') as file:
                csvreader = csv.DictReader(file)
                for rows in csvreader:
                    data.append(rows)
        
        return data

    def handle(self, *args, **kwargs):
        for question in Question.objects.filter(subject__isnull=False, updated_at__date=datetime.now().date(), grade__name="Curso"):
            question.grade = question.subject.knowledge_area.grades.all().exclude(
                name__in=["Curso", "Concurso."]
            ).order_by('name').last()
            question.save(skip_hooks=True)

        return
        
        TOPICS_FILE_PATH = "https://fiscallizeremote.nyc3.cdn.digitaloceanspaces.com/temp/topics.csv"

        for question in Question.objects.filter(subject__isnull=False, updated_at__date=datetime.now().date(), grade__name="Curso"):
            question.grade = question.subject.knowledge_area.grades.all().exclude(
                name__in=["Curso", "Concurso."]
            ).order_by('name').last()
            question.save(skip_hooks=True)
            
        public_questions = Question.objects.filter(
            source_question__isnull=True,
            is_public=True
        )

        topic_pks = public_questions.values_list("topics__pk", flat=True).distinct()

        topics = Topic.objects.filter(subject__client__isnull=True, pk__in=topic_pks).distinct()
        
        errors = {
            'notexists': [],
            'multipleobjects': [],
            'general': [],
        }
        
        for index, new_topic in enumerate(self.csv_to_dict(TOPICS_FILE_PATH)):
            try:
                old_topic = topics.get(subject__name=new_topic["Subject"], name=new_topic["Topic"])
                
                old_topic.name = new_topic["Topic"]
                
                theme=None
                
                if new_topic["Theme"]:
                    
                    theme, created = Theme.objects.get_or_create(
                        name=new_topic["Theme"],
                        client=None,
                        created_by=None
                    )
                    
                    old_topic.theme = theme
                    
                main_topic=None

                if new_topic["MainTopic"]:
                    main_topic, created = MainTopic.objects.get_or_create(
                        name=new_topic["MainTopic"],
                        theme=theme,
                        client=None,
                        created_by=None
                    )
                    
                    old_topic.main_topic = main_topic
                    
                print(f'Assunto {index + 1}: {old_topic.name.split(" ")[0]}')
                old_topic.save()
            
            except Topic.DoesNotExist as e:
                errors['notexists'].append(new_topic)
            except Topic.MultipleObjectsReturned as e:
                errors['multipleobjects'].append(topics.filter(name=new_topic["Topic"]).values('pk', 'name'))
            except Exception as e:
                errors['general'].append(e)
                
        print(f'{len(errors["notexists"])} não existe: {errors["notexists"]}, {errors["multipleobjects"]} multiplos objetos e {len(errors["general"])} em geral')