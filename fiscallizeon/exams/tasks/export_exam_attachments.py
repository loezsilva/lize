import os
import re
import io
import zipfile
import requests

from celery import states
from celery.exceptions import Ignore

from fiscallizeon.celery import app
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.exams.models import Exam, ExamQuestion
from fiscallizeon.questions.models import Question
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.answers.models import FileAnswer

def get_exam_attachments(exam_pk):
    exam = Exam.objects.get(pk=exam_pk)
    application_students = ApplicationStudent.objects.filter(
        application__exam=exam,
    ).distinct()

    exam_questions = ExamQuestion.objects.filter(
        exam=exam
    ).order_by(
        'exam_teacher_subject__order', 'order'
    )

    exam_dir = os.path.join(exam.name.replace('/', ' '))

    exam_name_no_spaces = re.sub(r'[\s]+|/', '_', exam.name)
    exam_name = re.sub(r'[^a-zA-Z0-9_]+', '', exam_name_no_spaces)
    zip_filename = f'/code/tmp/{exam_name}.zip'

    with zipfile.ZipFile(zip_filename, "a", zipfile.ZIP_DEFLATED, allowZip64=True) as zip_file:
        for index, exam_question in enumerate(exam_questions):
            if exam_question.question.category != Question.FILE:
                continue

            print(f'Getting Question {index + 1} answers')

            subject_name = 'Geral'
            if exam_question.exam_teacher_subject:
                subject_name = exam_question.exam_teacher_subject.teacher_subject.subject.name
            elif exam_question.question.subject:
                subject_name = exam_question.question.subject.name
            
            subject_name = subject_name.replace('/', ' ')
            enunciation_path = os.path.join('enunciados', f'Questão {index+1}.txt')
            enunciation = exam_question.question.get_enunciation_str()
            zip_file.writestr(enunciation_path, io.BytesIO(enunciation.encode('utf-8')).getvalue())

            for application_student in application_students:
                student = application_student.student

                answer = FileAnswer.objects.filter(
                    student_application=application_student,
                    question=exam_question.question,
                ).order_by(
                    'question__examquestion__order'
                ).distinct().last()
                
                if not answer:
                    continue
                
                students_classes = student.classes.all()
                class_path = os.path.join(exam_dir, str(students_classes[0]) if students_classes else str(student))
                subject_path = os.path.join(class_path, subject_name) 
                question_dir = os.path.join(subject_path, f'Questão {index+1}')

                _, file_extension = os.path.splitext(answer.arquivo.name.split('/')[-1])
                filename = os.path.join(question_dir, student.name + file_extension)
                
                response = requests.get(answer.arquivo.url)
                zip_file.writestr(filename, io.BytesIO(response.content).getvalue())

    fs = PrivateMediaStorage()
    final_filename = fs.save(
        f'devolutivas/{exam_name}.zip', 
        open(zip_filename, 'rb')
    )
    os.remove(zip_filename)
    return fs.url(final_filename)

@app.task(bind=True)
def export_exam_attachments(self, exam_pk):
    self.update_state(state=states.STARTED)
    try:
        file_url = get_exam_attachments(exam_pk)
        if file_url:
            self.update_state(state=states.SUCCESS, meta=file_url)
            return states.SUCCESS
        else:
            self.update_state(state=states.FAILURE)
            print('No files to export')
            raise Ignore()
    except Exception as e:
        print(e)
        self.update_state(state=states.FAILURE)
        raise Ignore()