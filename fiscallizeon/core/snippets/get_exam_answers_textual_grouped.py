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
    pk='ad450529-132c-4e9a-9587-a0c979a6c65a',
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
                    file_name = f'{student.name} ({student.enrollment_number}).txt'
                    textual_path = os.path.join(subject_path, 'discursivas')
                    os.makedirs(textual_path, exist_ok=True)
                    file_path = os.path.join(textual_path, file_name)
                    
                    with open(file_path, 'a+') as f:
                        f.write(f'- Questão {index + 1}:')
                        f.write('\n')
                        f.write(answer or '[ALUNO NÃO RESPONDEU]')
                        f.write('\n\n')

                    enunciation_dir = os.path.join(textual_path, 'enunciados')
                    os.makedirs(enunciation_dir, exist_ok=True)
                    enunciation_path = os.path.join(enunciation_dir, f'Questão {index + 1}')

                    if not os.path.isfile(enunciation_path):
                        with open(enunciation_path, 'w+') as f:
                            f.write(exam_question.question.get_enunciation_str())

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
                        choice_answers_score.append(exam_question.weight if answer.question_option.is_correct else '0')
                    else:
                        choice_answers_score.append(' ')

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

                    student_class = str(students_classes[0]) if students_classes else '-'
                    _csv_headers = ['Matricula', 'Turma', 'Aluno'] + csv_headers[subject_indexes[0]:subject_indexes[-1] + 1] + ['Corretas', 'Incorretas', 'Nota']
                    _choice_answers = [student.enrollment_number, student_class, student.name] + choice_answers[subject_indexes[0]:subject_indexes[-1] + 1]
                    _choice_answers_score = [student.enrollment_number, student_class, student.name] + choice_answers_score[subject_indexes[0]:subject_indexes[-1] + 1]

                    total_blank = _choice_answers_score.count(' ')
                    total_wrong = _choice_answers_score.count('0')
                    total_correct = len(choice_answers_score[subject_indexes[0]:subject_indexes[-1] + 1]) - total_wrong - total_blank
                    total_grade = sum([float(c) if c != ' ' else 0 for c in choice_answers_score[subject_indexes[0]:subject_indexes[-1] + 1]])

                    _choice_answers_score += [total_correct, total_wrong, total_grade]

                    write_csv_file(csv_path, _csv_headers, _choice_answers)
                    write_csv_file(csv_path_score, _csv_headers, _choice_answers_score)

        for subject in glob(os.path.join(exam_dir, '*/*/discursivas/')):
            subject_path = Path(subject).parent.absolute()
            
            with open(os.path.join(subject_path, 'discursivas_agrupadas.txt'), 'a+') as f:
                f.write('----------------------------------------------------------------\n')
                f.write('|                          ENUNCIADOS                          |\n')
                f.write('----------------------------------------------------------------\n\n')

            for enunciate_path in sorted(glob(os.path.join(subject, 'enunciados', '*'))):
                with open(enunciate_path, 'r+') as f:
                    enunciate = f.read()

                with open(os.path.join(subject_path, 'discursivas_agrupadas.txt'), 'a+') as f:
                    f.write(f'{str(enunciate_path).split("/")[-1]} - ')
                    f.write(enunciate)
                    f.write('\n\n')

            with open(os.path.join(subject_path, 'discursivas_agrupadas.txt'), 'a+') as f:
                f.write('----------------------------------------------------------------\n')
                f.write('|                          RESPOSTAS                           |\n')
                f.write('----------------------------------------------------------------\n\n')

            for student_path in sorted(glob(os.path.join(subject, '*.txt'))):
                with open(student_path, 'r+') as f:
                    answer = f.read()

                with open(os.path.join(subject_path, 'discursivas_agrupadas.txt'), 'a+') as f:
                    f.write(f'{str(student_path).split("/")[-1].replace(".txt", "")}:\n\n')
                    f.write(answer)
                    f.write('------------------------------------------------\n\n')
            
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
