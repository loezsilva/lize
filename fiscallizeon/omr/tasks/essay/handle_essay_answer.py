import os
import hashlib

from django.core.files.uploadedfile import UploadedFile

from fiscallizeon.celery import app
from fiscallizeon.omr.models import OMRUpload, OMRStudents, OMRDiscursiveScan, OMRDiscursiveError
from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.questions.models import Question
from fiscallizeon.answers.models import FileAnswer, TextualAnswer
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.omr.utils import download_spaces_image


@app.task(bind=True)
def handle_essay_answer(self, args):
    if not args:
        return
    
    upload_id, essay_question = args

    if not essay_question or not essay_question.get('exam_question_pk', None):
        return

    omr_upload = OMRUpload.objects.using('default').get(pk=upload_id)
    application_student = ApplicationStudent.objects.get(pk=essay_question['object_id'])
    
    exam_question = ExamQuestion.objects.get(pk=essay_question['exam_question_pk'])

    if exam_question.question.category == Question.TEXTUAL:
        exam_question.question.category = Question.FILE
        exam_question.question.save(skip_hooks=True)

    file_answer = FileAnswer.objects.filter(
        question=exam_question.question,
        student_application=application_student,
    ).first()

    if not file_answer:
        file_answer = FileAnswer.objects.create(
            question=exam_question.question,
            student_application=application_student,
        )

    tmp_file = download_spaces_image(essay_question['image_path'])
    file_answer.arquivo=UploadedFile(file=open(tmp_file, 'rb'))
    file_answer.save()

    if omr_error_pk := essay_question.get('omr_error', None):
        OMRDiscursiveError.objects.filter(pk=omr_error_pk).update(
            is_solved=True
        )

    textual_answer = TextualAnswer.objects.filter(
        question=exam_question.question,
        student_application=application_student,
    ).first()

    if textual_answer:
        grade = textual_answer.teacher_grade

        if grade != None:
            file_answer.teacher_grade = grade
            file_answer.save()

        textual_answer.delete()

    omr_student = OMRStudents.objects.filter(
        upload=omr_upload,
        application_student=application_student
    ).first()

    if not omr_student:
        omr_student = OMRStudents.objects.create(
            upload=omr_upload,
            application_student=application_student
        )

    omr_student.successful_questions_count += 1
    omr_student.save()

    if not application_student.is_omr:
        application_student.is_omr = True
        application_student.save(skip_hooks=True)

    OMRDiscursiveScan.objects.create(
        omr_student=omr_student,
        upload_image=UploadedFile(file=open(tmp_file, 'rb')),
        is_essay=True,
    )

    os.remove(tmp_file)

    return upload_id