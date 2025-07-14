import uuid
import re
import os
import shutil

import cv2
import requests

from fiscallizeon.celery import app
from fiscallizeon.omr.utils import process_qr
from fiscallizeon.core.gcp.ocr_service import get_ocr_image
from fiscallizeon.answers.models import FileAnswer, TextualAnswer
from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.questions.models import Question
from fiscallizeon.omr.models import OMRCategory
from fiscallizeon.omr.tasks.discursive.handle_discursive_answers import _get_question_grade


@app.task
def reprocess_file_answers(file_answer_id):
    RESULTS_DIR = '/code/tmp/fix-discursives'
    os.makedirs(RESULTS_DIR, exist_ok=True)

    file_answer = FileAnswer.objects.get(pk=file_answer_id)
    omr_category = OMRCategory.objects.get(sequential=8)

    tmp_file = os.path.join(RESULTS_DIR, f'{uuid.uuid4()}.jpg')
    with requests.get(file_answer.arquivo.url, stream=True) as r:
        with open(tmp_file, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

    exam_question = ExamQuestion.objects.filter(
        question=file_answer.question_id,
        exam=file_answer.student_application.application.exam_id
    ).first()

    if not exam_question:
        image = cv2.imread(tmp_file)
        h, w, _ = image.shape
        image_cropped = image[:int(h/2), int(w - w/6):w]
        qr_content = process_qr(image_cropped)

        if not qr_content:
            ocr_json = get_ocr_image(tmp_file)

            try:
                exam_question_code = None
                full_text = ocr_json['responses'][0]['fullTextAnnotation']['text']
                confidence = ocr_json['responses'][0]['fullTextAnnotation']['pages'][0]['confidence']

                if confidence < 0.6:
                    print("ExamQuestion não encontrada1")
                    return

                question_code_pattern = re.compile("#(.{4})#")
                if re_search := question_code_pattern.search(full_text):
                    exam_question_code = re_search.groups(0)[0]
                    if not exam_question_code:
                        print("ExamQuestion não encontrada2")
                        return

            except Exception as e:
                print("ExamQuestion não encontrada3", e)
                return
        else:
            exam_question_code = qr_content.replace('#', '')

        exam_question = ExamQuestion.objects.filter(
            short_code=exam_question_code,
            exam=file_answer.student_application.application.exam_id
        ).first()

        if not exam_question:
            print("ExamQuestion não encontrada4")
            return

    textual_answer = TextualAnswer.objects.filter(
        question=exam_question.question_id,
        student_application=file_answer.student_application
    ).first()

    if textual_answer and textual_answer.who_corrected:
        grade = textual_answer.teacher_grade
    else:
        grade = _get_question_grade(tmp_file, exam_question, omr_category)

    if grade != None:
        file_answer.teacher_grade = grade

    file_answer.question = exam_question.question
    file_answer.save()

    exam_question.question.category = Question.FILE
    exam_question.question.save()

    os.remove(tmp_file)
    print(f'FileAnswer processada {file_answer.pk} - nota: {file_answer.teacher_grade}')