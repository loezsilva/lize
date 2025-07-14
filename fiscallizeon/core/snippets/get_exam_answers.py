import os
import requests
import shutil
import pyexcel
from glob import glob
from datetime import datetime

from fiscallizeon.clients.models import Client
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.exams.models import Exam, ExamQuestion
from fiscallizeon.students.models import Student
from fiscallizeon.questions.models import Question, QuestionOption
from fiscallizeon.answers.models import FileAnswer, OptionAnswer, TextualAnswer

#CLIENT_PK = 'c1e071a4-d0c0-48f5-a820-8a0c9e914c33'  #MARISTA
#CLIENT_PK = 'f1a6a4e9-7b95-4045-b6dd-f720a17a14e1' #LATO
DATE = datetime(year=2021, month=3, day=13)

TARGET_DIR = './exam_answers'

def write_csv_file(filepath, headers, row):
    import csv
    csv_exists = os.path.isfile(filepath)

    with open(filepath, mode='a') as choices_file:
        writer = csv.writer(
            choices_file, 
            delimiter=',', 
            quotechar='"', 
            quoting=csv.QUOTE_ALL,
        )

        if not csv_exists:
            writer.writerow(headers)

        writer.writerow(row)

client = Client.objects.get(pk=CLIENT_PK)
applications = Application.objects.filter(date=DATE)
exams = Exam.objects.filter(
    application__in=applications,
    coordinations__unity__client=client,
).distinct()

print(f'Exporting {exams.count()} exams...\n\n')

try:
    for exam in exams:
        application_students = ApplicationStudent.objects.filter(
            application__exam=exam,
            start_time__date=DATE,
        ).distinct()

        exam_questions = ExamQuestion.objects.filter(exam=exam).order_by('exam_teacher_subject__order', 'order')

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
                if exam_question.question.category == Question.TEXTUAL:
                    student_answer = TextualAnswer.objects.filter(
                        student_application=application_student,
                        question=exam_question.question
                    ).order_by(
                        'created_at'
                    ).distinct().last()  
                    
                    answer = student_answer.content if student_answer else None
                    file_name = f'Questão {index+1}.txt'
                    file_path = os.path.join(subject_path, file_name)

                    file_exists = os.path.isfile(file_path)
                    
                    with open(file_path, 'a+') as f:
                        if not file_exists:
                            f.write(str(exam_question.question))
                            f.write('\n\n')

                        f.write(f'- {student.name.upper()}:')
                        f.write('\n')
                        f.write(answer or '[ALUNO NÃO RESPONDEU]')
                        f.write('\n\n')

                elif exam_question.question.category == Question.FILE:
                    answer = FileAnswer.objects.filter(
                        student_application=application_student,
                        question=exam_question.question,
                    ).order_by(
                        'question__examquestion__order'
                    ).distinct().last()
                    
                    if not answer:
                        continue

                    response = requests.get(answer.arquivo.url, stream=True)
                    
                    question_dir = os.path.join(subject_path, f'Questão {index+1}')
                    os.makedirs(question_dir, exist_ok=True)

                    enunciation_path = os.path.join(question_dir, f'enunciado.txt')
                    if not os.path.isfile(enunciation_path):
                        with open(enunciation_path, 'w+') as f:
                            f.write(exam_question.question.get_enunciation_str())
                    
                    _, file_extension = os.path.splitext(answer.arquivo.name.split('/')[-1])
                    filename = os.path.join(question_dir, student.name + file_extension)

                    with open(filename, "wb") as f:
                        shutil.copyfileobj(response.raw, f)

                elif exam_question.question.category == Question.CHOICE:
                    answer = OptionAnswer.objects.filter(
                        student_application=application_student,
                        question_option__question=exam_question.question,
                        status=OptionAnswer.ACTIVE,
                    ).distinct().order_by('created_at').last()

                    csv_headers.append(f'Questão {index+1}')
                    subjects_list.append(subject_name)
                    choice_answers.append(str(answer.question_option)[:50] if answer else 'Não respondida')
                    if answer and answer.question_option.question.has_feedback:
                        choice_answers_score.append('C' if answer.question_option.is_correct else 'E')
                    else:
                        choice_answers_score.append('X')

            if choice_answers:
                subjects = set(subjects_list)

                for subject in subjects:
                    subject_path = os.path.join(class_path, subject)
                    os.makedirs(subject_path, exist_ok=True)

                    csv_path = os.path.join(subject_path, 'objetivas.csv')
                    csv_path_score = os.path.join(subject_path, 'objetivas_score.csv')

                    subject_indexes = []
                    for i, val in enumerate(subjects_list):
                        if val==subject:
                            subject_indexes.append(i)


                    _csv_headers = ['Aluno'] + csv_headers[subject_indexes[0]:subject_indexes[-1] + 1] + ['Corretas', 'Incorretas']
                    _choice_answers = [student.name] + choice_answers[subject_indexes[0]:subject_indexes[-1] + 1]
                    _choice_answers_score = [student.name] + choice_answers_score[subject_indexes[0]:subject_indexes[-1] + 1]

                    total_correct = _choice_answers_score.count('C')
                    total_wrong = _choice_answers_score.count('E')

                    _choice_answers_score += [total_correct, total_wrong]

                    write_csv_file(csv_path, _csv_headers, _choice_answers)
                    write_csv_file(csv_path_score, _csv_headers, _choice_answers_score)

    #Generate XLSX
    files = glob(f'{TARGET_DIR}/**/*.csv', recursive=True)

    for f in files:
        filename, file_extension = os.path.splitext(f)
        sheet = pyexcel.get_sheet(file_name=f, delimiter=",")
        sheet.save_as(f'{filename}.xlsx')

except Exception as e:
    import sys, os
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print(exc_type, fname, exc_tb.tb_lineno, e)
