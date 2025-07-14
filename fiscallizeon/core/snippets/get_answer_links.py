'''
Retorna os arquivos anexados das provas do array 'exams_pks' na estrutura:
Cliente/Turma/Questão/arquivo_aluno 
'''

import os
import re
import requests
import shutil

from django.utils.html import strip_tags

from fiscallizeon.exams.models import Exam
from fiscallizeon.students.models import Student
from fiscallizeon.answers.models import FileAnswer

TARGET_DIR = 'file_answers'
exams_pks = ['e2479355-3ae4-40cb-bde5-ce87469aeef9']

regex = re.compile('[^a-zA-Z]\s\n')

exams = Exam.objects.filter(pk__in=exams_pks)

students = Student.objects.filter(applications__exam__in=exams)

for student in students:
    print(f'Downloading answers from student {student}')
    student_answers = FileAnswer.objects.filter(
        student_application__student=student,
        student_application__application__exam__in=exams,
    ).order_by(
        'question__examquestion__order'
    ).distinct()

    if not student_answers:
        continue

    client_path = os.path.join(TARGET_DIR, student.client.name.upper())
    class_path = os.path.join(client_path, student.classes.all()[0].name)

    for answer in student_answers:
        qustion_name = regex.sub('', strip_tags(str(answer.question.enunciation_escaped()))[:50])
        question_path = os.path.join(class_path, qustion_name)

        filename, file_extension = os.path.splitext(answer.arquivo.name.split('/')[-1])
        filedir = os.path.join(question_path, str(student).upper() + file_extension)

        if os.path.exists(filedir):
            continue

        os.makedirs(os.path.dirname(filedir), exist_ok=True)

        response = requests.get(answer.arquivo.url, stream=True)

        with open(filedir, "wb") as f:
            shutil.copyfileobj(response.raw, f)
        
        del response