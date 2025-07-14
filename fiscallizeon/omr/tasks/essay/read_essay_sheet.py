import os
import uuid
import re
import cv2

from django.core.files.uploadedfile import UploadedFile

from fiscallizeon.celery import app
from fiscallizeon.omr.models import OMRUpload, OMRCategory, OMRError, OMRDiscursiveError
from fiscallizeon.exams.models import ExamQuestion
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.omr.utils import process_qr, download_spaces_image
from fiscallizeon.core.gcp.ocr_service import get_ocr_image


def identify_question(omr_upload, application_student, image_path, randomization_version=0):
    upload_base_dir = f'tmp/{omr_upload.id}'
    tmp_dir = os.path.join(upload_base_dir, 'qr-tmp')
    os.makedirs(tmp_dir, exist_ok=True)

    exam_question_code = None

    image = cv2.imread(image_path)
    h, w, _ = image.shape

    image_cropped = image[h-int(h/5):, w-int(w/4):w]
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
                return

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
            return

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
        return

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
        return

    fs = PrivateMediaStorage()
    filename = fs.save(
        f"answers/file/tmp/{omr_upload.pk}/{image_path.split('/')[-1]}",
        open(image_path, 'rb')
    )
    
    essay_question = {
        'object_id': str(application_student.pk),
        'exam_question_pk': str(exam_question.pk),
        'image_path': filename,
    }
    return essay_question


@app.task
def read_essay_sheet(upload_id, discursive_upload):
    omr_upload = OMRUpload.objects.get(pk=upload_id)

    application_student = ApplicationStudent.objects.using('default').filter(pk=discursive_upload['object_id']).first()
    randomization_version = discursive_upload.get('randomization_version', 0)

    if not application_student:
        OMRError.objects.create(
            upload=omr_upload,
            application=omr_upload.application,
            omr_category=OMRCategory.objects.get(sequential=discursive_upload['sequential']),
            error_image=discursive_upload['file_path'],
            category=OMRError.STUDENT_NOT_FOUND,
            page_number=discursive_upload.get('page_number', 0),
        )
        return
    
    if application := omr_upload.application:
        application_student.application = application
        application_student.save()

    tmp_image = download_spaces_image(discursive_upload['file_path'])
    essay_question = identify_question(omr_upload, application_student, tmp_image, randomization_version)
    os.remove(tmp_image)

    if omr_error_id := discursive_upload.get('omr_error_id', None):
        omr_error = OMRError.objects.get(pk=omr_error_id)
        omr_error.is_solved = True
        omr_error.save()

    return (upload_id, essay_question)