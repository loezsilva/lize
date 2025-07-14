import re
import math
import glob
import os
import uuid
import cv2
import numpy as np

from django.core.files.uploadedfile import UploadedFile

from fiscallizeon.celery import app
from fiscallizeon.omr.utils import process_qr
from fiscallizeon.omr.models import OMRUpload, OMRError, OMRCategory
from fiscallizeon.applications.models import Application, ApplicationStudent
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
            return image
    except Exception as e:
        return image

    rows,cols = image.shape[:2]
    center = (cols/2, rows/2)
    M = cv2.getRotationMatrix2D(center, np.array(angles).mean(), 1)
    return cv2.warpAffine(image, M, (image.shape[1], image.shape[0]), flags=cv2.INTER_LINEAR)

def handle_answer_scan(upload_id, image_path):
    raw_image = cv2.imread(image_path)

    #Adicionando bordas brancas nas laterais
    zeros = np.zeros((raw_image.shape[0], 30, 3), dtype=np.uint8) + 255
    bordered_image = np.hstack((zeros, raw_image, zeros))

    image = _align_image_x(bordered_image)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blured = cv2.GaussianBlur(gray, (7,7), 0)
    _, thresh = cv2.threshold(blured, 150, 255, cv2.THRESH_BINARY_INV)

    kernel = np.ones((5,5),np.uint8)
    opening = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel, iterations=1)

    cnts = cv2.findContours(opening, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]

    orig_hight, orig_width = image.shape[:2]
    croped_areas = []

    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.015 * peri, True)

        _, _, w, h = cv2.boundingRect(approx)
        if w < orig_width * 0.7 or h < orig_hight * 0.05:
            continue

        x, y, w, h = cv2.boundingRect(approx)
        croped_areas.append(image[y:y+h, x:x+w])

    cropped_image_dir = f'tmp/{upload_id}/elit-crop'
    os.makedirs(cropped_image_dir, exist_ok=True)

    cropped_final_images_paths = []
    for croped_answer in croped_areas:
        croped_image_path = os.path.join(cropped_image_dir, f'{uuid.uuid4()}.jpg') 
        cropped_final_images_paths.append(croped_image_path)
        cv2.imwrite(croped_image_path, croped_answer)

    return cropped_final_images_paths

def identify_students(upload_id, cropped_answers_paths):
    questions_student = []

    upload_base_dir = f'tmp/{upload_id}'
    tmp_dir = os.path.join(upload_base_dir, 'qr-tmp')
    os.makedirs(tmp_dir, exist_ok=True)

    omr_upload = OMRUpload.objects.get(pk=upload_id)
    omr_category = OMRCategory.objects.get(sequential=OMRCategory.ELIT)

    for image_path in cropped_answers_paths:
        instance_id = ''

        image = cv2.imread(image_path)
        w = image.shape[1]

        image_cropped = image[:, int(w - w/2):w]
        qr_content = process_qr(image_cropped) or ''

        if not qr_content:
            tmp_filename = os.path.join(tmp_dir, f'qr_student_{uuid.uuid4()}.jpg')
            cv2.imwrite(tmp_filename, image_cropped)
            ocr_json = get_ocr_image(tmp_filename)

            try:
                full_text = ocr_json['responses'][0]['fullTextAnnotation']['text']
                confidence = ocr_json['responses'][0]['fullTextAnnotation']['pages'][0]['confidence']

                if confidence < 0.6:
                    OMRError.objects.create(
                        upload=omr_upload,
                        category=OMRError.QR_UNRECOGNIZED,
                        omr_category=OMRCategory.ELIT,
                        error_image=UploadedFile(
                            file=open(image_path, 'rb')
                        ),
                    )
                    continue

                full_text = full_text.replace(' ', '-')
                full_text = full_text.replace('O', '0')

                question_code_pattern = re.compile("#(.*)#")
                if re_search := question_code_pattern.search(full_text):
                    qr_content = str(re_search.groups(0)[0])

            except Exception as e:
                print(f"# FAIL TO READ ELIT QR: {e}")
                OMRError.objects.create(
                    upload=omr_upload,
                    category=OMRError.QR_UNRECOGNIZED,
                    omr_category=OMRCategory.ELIT,
                    error_image=UploadedFile(
                        file=open(image_path, 'rb')
                    ),
                )
                continue

        try:
            operation_type, instance_id = qr_content.replace('#', '').split(':')
            instance_id = uuid.UUID(instance_id)
        except:
            OMRError.objects.create(
                upload=omr_upload,
                category=OMRError.QR_UNRECOGNIZED,
                omr_category=omr_category,
                error_image=UploadedFile(
                    file=open(image_path, 'rb')
                ),
            )
            continue
        
        if operation_type == 'A':
            application = Application.objects.filter(pk=instance_id).first()
            OMRError.objects.create(
                upload=omr_upload,
                application=application,
                category=OMRError.STUDENT_NOT_FOUND,
                omr_category=omr_category,
                error_image=UploadedFile(
                    file=open(image_path, 'rb')
                ),
            )
            continue

        application_student = ApplicationStudent.objects.filter(pk=instance_id).first()
        if not application_student:
            OMRError.objects.create(
                upload=omr_upload,
                category=OMRError.QR_UNRECOGNIZED,
                omr_category=omr_category,
                error_image=UploadedFile(
                    file=open(image_path, 'rb')
                ),
            )
            continue

        questions_student.append({
            'application_student_pk': str(application_student.pk),
            'image_path': image_path,
        })

    return questions_student

@app.task
def crop_answer_area(upload_id):
    return_elit_uploads = []

    pages_paths = glob.glob(f'tmp/{upload_id}/*.jpg')

    for page_path in pages_paths:
        cropped_answers_raw_paths = handle_answer_scan(upload_id, page_path)
        elit_upload = identify_students(upload_id, cropped_answers_raw_paths)

        return_elit_uploads.extend(elit_upload)

    return (upload_id, return_elit_uploads)