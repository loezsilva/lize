import re
import math
import os
import uuid
import cv2
import numpy as np
from unidecode import unidecode

from django.core.files.uploadedfile import UploadedFile

from fiscallizeon.celery import app
from django.conf import settings
from fiscallizeon.omr.utils import process_qr, download_spaces_image
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.omr.models import OMRUpload, OMRError, OMRCategory, OMRDiscursiveError
from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.core.gcp.ocr_service import get_ocr_image


def _align_image_x(image):
    _,w = image.shape[:2]
    gray = cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    blured = cv2.GaussianBlur(gray, (7,7), 0)
    _, thresh = cv2.threshold(blured, 150, 255, cv2.THRESH_BINARY_INV)

    try:
        angles = []
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40,1))
        detect_horizontal = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
        cnts = cv2.findContours(detect_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = cnts[0] if len(cnts) == 2 else cnts[1]
        for c in cnts:
            length = cv2.arcLength(c, True)
            if length < w * 0.7:
                continue

            [vx, vy, _, _] = cv2.fitLine(c, cv2.DIST_L2, 0, 0.01, 0.01)
            angle = math.atan2(vy, vx) * 180.0 / math.pi
            angles.append(angle)

        if not angles:
            raise Exception("Ângulos não detectados!")

    except Exception as e:
        if settings.DEBUG:
            print(f"Erro de alinhamento no eixo x: {e}")
        return image

    rows,cols = image.shape[:2]
    center = (cols/2, rows/2)
    M = cv2.getRotationMatrix2D(center, np.array(angles).mean(), 1)
    return cv2.warpAffine(image, M, (image.shape[1], image.shape[0]), flags=cv2.INTER_LINEAR)

def handle_answer_scan(upload_id, image_path, application_student):
    raw_image = cv2.imread(image_path)

    #Adicionando bordas brancas nas laterais
    zeros_h = np.zeros((raw_image.shape[0], 30, 3), dtype=np.uint8) + 255
    bordered_image = np.hstack((zeros_h, raw_image, zeros_h))

    gray = cv2.cvtColor(bordered_image, cv2.COLOR_BGR2GRAY)
    blured = cv2.GaussianBlur(gray, (7,7), 0)
    _, thresh = cv2.threshold(blured, 150, 255, cv2.THRESH_BINARY_INV)

    kernel = np.ones((5,5),np.uint8)
    opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)

    cnts = cv2.findContours(opening, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]

    orig_hight, orig_width = bordered_image.shape[:2]
    croped_areas = []

    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.015 * peri, True)

        _, _, w, h = cv2.boundingRect(approx)
        if w < orig_width * 0.8 or h < orig_hight * 0.1:
            continue

        x, y, w, h = cv2.boundingRect(approx)
        croped_areas.append(bordered_image[y:y+h, x:x+w])

    cropped_image_dir = f'tmp/{upload_id}/discursive-crop'
    os.makedirs(cropped_image_dir, exist_ok=True)

    cropped_final_images_paths = []
    for croped_answer in croped_areas:
        _, width  = croped_answer.shape[:2]

        student_data_image = np.zeros((100, width, 3), np.uint8)
        student_data_image.fill(255)
        font = cv2.FONT_HERSHEY_COMPLEX

        student = application_student.student
        try:
            student_name = unidecode(student.name)
            exam_name = unidecode(application_student.application.exam.name)
        except Exception as e:
            student_name = student.name
            exam_name = application_student.application.exam.name

        cv2.putText(student_data_image, f'ALUNO: {student_name} ({student.enrollment_number})', (30,35), font, 1, (0, 0, 0), 2, cv2.LINE_AA)
        cv2.putText(student_data_image, f'CADERNO: {exam_name}', (30,75), font, 1, (0, 0, 0), 2, cv2.LINE_AA)

        aligned_croped_answer = _align_image_x(croped_answer)

        final_answer = np.vstack((aligned_croped_answer, student_data_image))
        croped_image_path = os.path.join(cropped_image_dir, f'{application_student.pk}_{uuid.uuid4()}.jpg')
        
        cropped_final_images_paths.append(croped_image_path)
        cv2.imwrite(croped_image_path, final_answer)
    return cropped_final_images_paths

def identify_questions(upload_id, application_student, cropped_answers_paths, randomization_version=0):
    questions_student = []

    upload_base_dir = f'tmp/{upload_id}'
    tmp_dir = os.path.join(upload_base_dir, 'qr-tmp')
    os.makedirs(tmp_dir, exist_ok=True)

    omr_upload = OMRUpload.objects.get(pk=upload_id)

    for image_path in cropped_answers_paths:
        exam_question_code = None

        image = cv2.imread(image_path)
        h, w, _ = image.shape

        image_cropped = image[:int(h/2), int(w - w/6):w]
        qr_content = process_qr(image_cropped)

        if not qr_content:
            tmp_filename = os.path.join(tmp_dir, f'qr_examquestion_{uuid.uuid4()}.jpg')
            cv2.imwrite(tmp_filename, image_cropped)
            ocr_json = get_ocr_image(tmp_filename)

            try:
                full_text = ocr_json['responses'][0]['fullTextAnnotation']['text']
                confidence = ocr_json['responses'][0]['fullTextAnnotation']['pages'][0]['confidence']

                if confidence < 0.6:
                    OMRDiscursiveError.objects.create(
                        upload=omr_upload,
                        application_student=application_student,
                        version_number=randomization_version or 0,
                        category=OMRDiscursiveError.QUESTION_NOT_FOUND,
                        error_image=UploadedFile(
                            file=open(image_path, 'rb')
                        ),
                    )
                    continue

                question_code_pattern = re.compile("#(.{4})#")
                if re_search := question_code_pattern.search(full_text):
                    exam_question_code = re_search.groups(0)[0]

            except Exception as e:
                print(f"# Fail to read discursive ExamQuestion QR: {e}")
                OMRDiscursiveError.objects.create(
                        upload=omr_upload,
                        application_student=application_student,
                        version_number=randomization_version or 0,
                        category=OMRDiscursiveError.QUESTION_NOT_FOUND,
                        error_image=UploadedFile(
                            file=open(image_path, 'rb')
                        ),
                    )
                continue

        else:
            exam_question_code = qr_content.replace('#', '')

        if not exam_question_code:
            print("QUESTÃO NÃO ENCONTRADA: SEM SHORT CODE")
            OMRDiscursiveError.objects.create(
                upload=omr_upload,
                application_student=application_student,
                version_number=randomization_version or 0,
                category=OMRDiscursiveError.QUESTION_NOT_FOUND,
                error_image=UploadedFile(
                    file=open(image_path, 'rb')
                ),
            )
            continue

        exam_question = ExamQuestion.objects.filter(
            short_code=exam_question_code,
            exam=application_student.application.exam_id
        ).first()

        if not exam_question:
            print("QUESTÃO NÃO ENCONTRADA: NÃO HÁ EXAM QUESTION PARA SHORT CODE")
            OMRDiscursiveError.objects.create(
                upload=omr_upload,
                application_student=application_student,
                version_number=randomization_version or 0,
                category=OMRDiscursiveError.QUESTION_NOT_FOUND,
                error_image=UploadedFile(
                    file=open(image_path, 'rb')
                ),
            )
            continue

        fs = PrivateMediaStorage()
        filename = fs.save(
            f"answers/file/tmp/{upload_id}/{image_path.split('/')[-1]}",
            open(image_path, 'rb')
        )
        
        questions_student.append({
            'application_student_pk': str(application_student.pk),
            'exam_question_pk': str(exam_question.pk),
            'image_path': filename,
        })

    return questions_student

@app.task
def crop_answer_area(upload_id, discursive_upload):
    omr_upload = OMRUpload.objects.get(pk=upload_id)

    application_student = ApplicationStudent.objects.using('default').filter(pk=discursive_upload['object_id']).first()
    randomization_version = discursive_upload.get('randomization_version', 0)

    if not application_student:
        OMRError.objects.create(
            upload=omr_upload,
            omr_category=OMRCategory.objects.get(sequential=discursive_upload['sequential']),
            application=omr_upload.application,
            error_image=discursive_upload['file_path'],
            category=OMRError.STUDENT_NOT_FOUND,
            page_number=discursive_upload.get('page_number', 0),
        )
        return
    
    if application := omr_upload.application:
        application_student.application = application
        application_student.save()

    tmp_image = download_spaces_image(discursive_upload['file_path'])
    cropped_answers_raw_paths = handle_answer_scan(upload_id, tmp_image, application_student)
    discursive_upload['answers_data'] = identify_questions(upload_id, application_student, cropped_answers_raw_paths, randomization_version)
    os.remove(tmp_image)

    if omr_error_id := discursive_upload.get('omr_error_id', None):
        omr_error = OMRError.objects.get(pk=omr_error_id)
        omr_error.is_solved = True
        omr_error.save()

    return (upload_id, discursive_upload)