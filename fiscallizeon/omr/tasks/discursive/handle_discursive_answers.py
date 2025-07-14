import cv2
import numpy as np

import io
import os
import shutil
import uuid
import hashlib
from decimal import Decimal

import requests

from celery import states

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile

from fiscallizeon.core.retry import retry
from fiscallizeon.celery import app
from fiscallizeon.omr.models import OMRUpload, OMRStudents, OMRDiscursiveScan, OMRCategory, OMRDiscursiveError
from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.questions.models import Question
from fiscallizeon.answers.models import FileAnswer, TextualAnswer
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.omr.utils import download_spaces_image
from fiscallizeon.omr.functions.main import process_file
from fiscallizeon.core.gcp.utils import get_service_account_oauth2_token
from fiscallizeon.core.requests_utils import get_session_retry


"""
DEPRECATED: estava gerando muitos falsos positivos
"""
@retry(tries=6)
def _get_question_grade_gcp(image_url, exam_question, omr_category):
    auth_token = get_service_account_oauth2_token(settings.GCP_DISCURSIVE_CORRECTION_URL)
    headers = {"Authorization": f"Bearer {auth_token}"}
    body = {'url': image_url}

    session = get_session_retry()
    correction_url = settings.GCP_DISCURSIVE_CORRECTION_URL + '/get_discursive_grade'
    with session.post(correction_url, json=body, headers=headers, timeout=60) as response:
        if response.status_code >= 500:
            raise Exception('HTTP error')

    try:
        response = response.json()

        if settings.DEBUG:
            print(image_url)
            print(f'Response: {response}')

        confidence = float(response.get('confidence', 0))
        read_answer = response.get('class', 'I')

        if confidence < 0.9 or read_answer in ['I', '0']:
            print(f'Low confidence/empty answer: {response}')
            return None

        option_index = 'ABCDE'.index(read_answer)
    except Exception as e:
        print('Problema ao identificar nota do professor na questão discursiva:', {e})
        return None

    if not omr_category.discursive_grade_setps:
        return None

    step_value = Decimal(round(1/(omr_category.discursive_grade_setps - 1), 6))
    return option_index * step_value * exam_question.weight


"""
DEPRECATED: utiliza localização de padrão de imagem (notas) que não funciona de maneira satisfatória
"""
def _get_question_grade_old(image_path, exam_question, omr_category):
    def _count_circles(image):
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        except:
            return 0
        
        rows = gray.shape[0]
        circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, rows / 8,
                                param1=200, param2=30,
                                minRadius=5, maxRadius=40)

        if circles is not None:
            circles = np.uint16(np.around(circles))
            return len(circles[0])
        return 0

    #Salvar o marcador de discursivas caso ainda não tenha em uma pasta temporária
    marker_path = os.path.join('/tmp', f'{omr_category.pk}.jpg')
    if not os.path.exists(marker_path):
        with requests.get(omr_category.marker_image.url, stream=True) as r:
            with open(marker_path, 'wb') as f:
                shutil.copyfileobj(r.raw, f)

    image = cv2.imread(image_path)

    img_cropped = None
    resize_values = [1585, 1570, 1555, 1600, 1615, 1630, 1645]
    for resize_value in resize_values:
        #Redimensionamento para ajustar às proporções do marcador
        h, w = image.shape[:2]
        factor = resize_value / w
        resized_image = cv2.resize(image, (int(w * factor), int(h * factor)))

        w = resized_image.shape[1]
        img_cropped = resized_image[:, int(w-w/9):w]
        omr_area = cv2.minMaxLoc(cv2.matchTemplate(img_cropped, cv2.imread(marker_path), cv2.TM_CCOEFF_NORMED))

        try:
            _point = omr_area[3]
        except Exception as e:
            print("Template não localizado na resposta", e)
            return None
        
        _point = (_point[0], _point[1] - 50)
        img_cropped = img_cropped[_point[1]:_point[1] + 180, _point[0]:_point[0] + 80]

        if img_cropped is None:
            print("img_cropped is NONE!")
            continue
        
        if _count_circles(img_cropped) >= 5:
            print(f"Contagem de círculos não funcionou")
            break

        img_cropped = None

    if img_cropped is None:
        return None

    _, buffer = cv2.imencode(".jpg", img_cropped)
    io_buf = io.BytesIO(buffer)
    grade_dict = process_file(io_buf, omr_category.template, file_buffered=True)
    
    checked_option = grade_dict.get('grade', '')
    if len(checked_option) != 1:
        return None

    try:
        option_index = 'ABCDEFGHIJ'.index(checked_option)
    except ValueError:
        return None

    if not omr_category.discursive_grade_setps:
        return None

    step_value = Decimal(round(1/(omr_category.discursive_grade_setps - 1), 6))
    return option_index * step_value * exam_question.weight


def _get_question_grade(image_path, exam_question, omr_category):
    image = cv2.imread(image_path)
    w = image.shape[1]
    img_cropped = image[:int(w/5), w-int(w/13):w]

    _, buffer = cv2.imencode(".jpg", img_cropped)
    io_buf = io.BytesIO(buffer)
    grade_dict = process_file(io_buf, omr_category.template, file_buffered=True)
    
    checked_option = grade_dict.get('grade', '')
    if len(checked_option) != 1:
        return None

    try:
        option_index = 'ABCDEFGHIJ'.index(checked_option)
    except ValueError:
        return None

    if not omr_category.discursive_grade_setps:
        return None

    step_value = Decimal(round(1/(omr_category.discursive_grade_setps - 1), 6))
    return option_index * step_value * exam_question.weight


@app.task(bind=True)
def handle_discursive_answers(self, args):
    if not args:
        return
    
    upload_id, discursive_upload = args

    omr_upload = OMRUpload.objects.using('default').get(pk=upload_id)
    application_student = ApplicationStudent.objects.get(pk=discursive_upload['object_id'])

    discursive_questions_count = 0
    for answer_data in discursive_upload['answers_data']:
        exam_question = ExamQuestion.objects.get(pk=answer_data['exam_question_pk'])

        if exam_question.question.category == Question.TEXTUAL:
            exam_question.question.category = Question.FILE
            exam_question.question.save(skip_hooks=True)

        if discursive_upload.get('ignore_question_corrected', False):
            already_corrected = FileAnswer.objects.filter(
                question=exam_question.question,
                student_application=application_student,
                who_corrected__isnull=False
            ).exists()

            if already_corrected:
                continue

        file_answer = FileAnswer.objects.filter(
            question=exam_question.question,
            student_application=application_student,
        ).first()

        textual_answer = TextualAnswer.objects.filter(
            question=exam_question.question,
            student_application=application_student,
        ).first()

        if not file_answer:
            file_answer = FileAnswer.objects.create(
                question=exam_question.question,
                student_application=application_student,
            )
            discursive_questions_count += 1

        tmp_file = download_spaces_image(answer_data['image_path'])
        file_answer.arquivo=UploadedFile(file=open(tmp_file, 'rb'))
        file_answer.save()

        omr_category = OMRCategory.objects.filter(sequential=discursive_upload['sequential']).first()

        grade = None
        if discursive_upload.get('auto_correct_discursives', False):
            grade = _get_question_grade(tmp_file, exam_question, omr_category)
            os.remove(tmp_file)
        elif textual_answer:
            grade = textual_answer.teacher_grade

        if grade != None:
            file_answer.teacher_grade = grade
            file_answer.save()

            if textual_answer:
                textual_answer.delete()

        if omr_error_pk := answer_data.get('omr_error', None):
            OMRDiscursiveError.objects.filter(pk=omr_error_pk).update(
                is_solved=True
            )

    omr_student = OMRStudents.objects.filter(
        upload=omr_upload,
        application_student=application_student
    ).first()

    if not omr_student:
        omr_student = OMRStudents.objects.create(
            upload=omr_upload,
            application_student=application_student
        )

    omr_student.successful_questions_count += discursive_questions_count
    omr_student.save()

    application_student.is_omr = True
    application_student.save(skip_hooks=True)

    if not any('omr_error' in obj for obj in discursive_upload['answers_data']):
        try:
            tmp_file = download_spaces_image(discursive_upload['file_path'])
            with open(tmp_file, 'rb') as f:
                image_hash = hashlib.md5(f.read()).hexdigest()
                previous_scan = OMRDiscursiveScan.objects.filter(
                    omr_student=omr_student,
                    image_hash=image_hash,
                ).first()
        except Exception as e:
            previous_scan = []
            image_hash = None
            print(f"Erro no cadastro de página de resposta discursiva {e}")

        if not previous_scan and not discursive_upload.get('ignore_omr_scan', False):
            OMRDiscursiveScan.objects.create(
                omr_student=omr_student,
                image_hash=image_hash,
                upload_image=discursive_upload['file_path'],
            )
        elif previous_scan:
            OMRDiscursiveScan.objects.create(
                omr_student=omr_student,
                image_hash=previous_scan.image_hash,
                upload_image=previous_scan.upload_image,
            )

    return upload_id