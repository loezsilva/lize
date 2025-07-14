import os
import requests
import shutil
import pyexcel
from glob import glob
from datetime import datetime
from pathlib import Path

from fiscallizeon.clients.models import Client
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.exams.models import Exam, ExamQuestion
from fiscallizeon.students.models import Student
from fiscallizeon.questions.models import Question, QuestionOption
from fiscallizeon.answers.models import FileAnswer, OptionAnswer, TextualAnswer

CLIENT_PK = 'c1e071a4-d0c0-48f5-a820-8a0c9e914c33'  #MARISTA
#CLIENT_PK = 'fd0d6523-c932-43b6-836c-695dd87880a4'  #SENAC
#CLIENT_PK = '4d5ad010-fa80-4359-ac82-99faebc3519a'  #SAO JOSE
#CLIENT_PK = 'ca7c4dd5-c327-4b99-b991-cbf749ff880e'  #DOM BOSCO
#CLIENT_PK = 'f1a6a4e9-7b95-4045-b6dd-f720a17a14e1'  #LATO
#CLIENT_PK = '60c76b23-e58e-44de-997f-821f3b26993d' #CEI
#CLIENT_PK = '29ab1ef5-64c3-433f-94ed-2c6b64112f55' #COGNITIVO
#CLIENT_PK = '47073c60-c3a8-4b8b-9319-d72c3e8165f9' #NOILDE


DATE = datetime(year=2021, month=4, day=22)

TARGET_DIR = './exam_answers'

client = Client.objects.get(pk=CLIENT_PK)
applications = Application.objects.filter(date=DATE)
exams = Exam.objects.filter(
    application__in=applications,
    coordinations__unity__client=client,
    #pk='ad450529-132c-4e9a-9587-a0c979a6c65a',
).distinct()

print(f'Exporting {exams.count()} exams...\n\n')

try:
    for exam in exams:
        application_students = ApplicationStudent.objects.filter(
            application__exam=exam,
            start_time__date=DATE,
        ).distinct()

        exam_questions = ExamQuestion.objects.filter(
            exam=exam,
            question__category=Question.FILE
        ).order_by(
            'exam_teacher_subject__order', 'order'
        )

        exam_dir = os.path.join(TARGET_DIR, exam.name.replace('/', ' '))
        os.makedirs(exam_dir, exist_ok=True)

        for application_student in application_students:
            student = application_student.student
            print(f'Getting answers for student {student}')
            
            answer = None
            csv_headers = []
            choice_answers = []
            choice_answers_score = []
            subjects_list = []

            students_classes = student.classes.all()
            class_path = os.path.join(exam_dir, str(students_classes[0]) if students_classes else str(student))
            os.makedirs(class_path, exist_ok=True)

            for index, exam_question in enumerate(exam_questions):
                subject_name = 'Geral'
                if exam_question.exam_teacher_subject:
                    subject_name = exam_question.exam_teacher_subject.teacher_subject.subject.name
                elif exam_question.question.subject:
                    subject_name = exam_question.question.subject.name
                

                subject_path = os.path.join(class_path, subject_name)
                os.makedirs(subject_path, exist_ok=True)
                
                answer = FileAnswer.objects.filter(
                    student_application=application_student,
                    question=exam_question.question,
                ).order_by(
                    'question__examquestion__order'
                ).distinct().last()
                
                if not answer:
                    continue

                response = requests.get(answer.arquivo.url, stream=True)
                
                question_dir = os.path.join(subject_path, 'anexos', f'Questão {index+1}')
                os.makedirs(question_dir, exist_ok=True)

                enunciation_path = os.path.join(question_dir, f'enunciado.txt')
                if not os.path.isfile(enunciation_path):
                    with open(enunciation_path, 'w+') as f:
                        f.write(exam_question.question.get_enunciation_str())
                
                _, file_extension = os.path.splitext(answer.arquivo.name.split('/')[-1])
                filename = os.path.join(question_dir, student.name + file_extension)

                with open(filename, "wb") as f:
                    shutil.copyfileobj(response.raw, f)


except Exception as e:
    import sys, os
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print(exc_type, fname, exc_tb.tb_lineno, e)
