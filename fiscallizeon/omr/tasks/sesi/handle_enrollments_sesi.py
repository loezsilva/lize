import os
import io
import re
import json

import cv2

from django.db.models import F, Value
from django.db.models.functions import Replace
from django.core.files.uploadedfile import UploadedFile

from fiscallizeon.celery import app
from fiscallizeon.core.gcp.ocr_service import get_ocr_image
from fiscallizeon.omr.utils import download_spaces_image, process_qr
from fiscallizeon.omr.models import OMRUpload, OMRError, OMRCategory
from fiscallizeon.students.models import Student
from fiscallizeon.applications.models import Application, ApplicationStudent


@app.task
def handle_enrollments_sesi(args):
    upload_id, omr_files = args

    omr_upload = OMRUpload.objects.using('default').get(pk=upload_id)
    omr_category = omr_upload.omr_category

    uploads_data = []

    for page_number, sheet_file in enumerate(sorted(omr_files), 1):
        tmp_file = download_spaces_image(sheet_file)
        
        sheet_data = {
            'path': sheet_file,
            'page_number': page_number,
        }

        if omr_upload.ignore_qr_codes:
            OMRError.objects.create(
                upload=omr_upload,
                omr_category=omr_category,
                error_image=UploadedFile(
                    file=open(tmp_file, 'rb')
                ),
                category=OMRError.QR_UNRECOGNIZED,
                page_number=page_number,
            )
            continue

        image = cv2.imread(tmp_file)
        h, w, _ = image.shape
        image_cropped = image[:int(h/4), w-int(w/3):w]
        qr_content = process_qr(image_cropped)

        student_name = None
        external_code = None
        if qr_content:
            try:
                qr_dict = json.loads(qr_content)
                student_name = qr_dict.get('pessoa', None)
                external_code = qr_dict.get('projeto', None)
            except Exception as e:
                print(e)
        else:
            image_cropped = image[:int(h/3), :w]
            _, buffer = cv2.imencode(".jpg", image_cropped)
            io_buf = io.BytesIO(buffer)
            ocr_json = get_ocr_image(io_buf, file_buffered=True)

            try:
                full_text = ocr_json['responses'][0]['fullTextAnnotation']['text']
                confidence = ocr_json['responses'][0]['fullTextAnnotation']['pages'][0]['confidence']

                if confidence > 0.8:
                    student_name = full_text.split('Estudante:')[1]
                    match = re.search(r'(.*)\s*\n?', student_name)
                    if match:
                        student_name = match.group(1).strip()
                else:
                    OMRError.objects.create(
                        upload=omr_upload,
                        omr_category=omr_category,
                        error_image=UploadedFile(
                            file=open(tmp_file, 'rb')
                        ),
                        category=OMRError.QR_UNRECOGNIZED,
                        page_number=page_number,
                    )
                    continue
            except Exception as e:
                OMRError.objects.create(
                    upload=omr_upload,
                    omr_category=omr_category,
                    error_image=UploadedFile(
                        file=open(tmp_file, 'rb')
                    ),
                    category=OMRError.QR_UNRECOGNIZED,
                    page_number=page_number,
                )
                continue

        print("STUDENT NAME", student_name)

        application = None
        if external_code:
            application = Application.objects.filter(exam__external_code=external_code).first()

        if not student_name:
            OMRError.objects.create(
                upload=omr_upload,
                omr_category=omr_category,
                error_image=UploadedFile(
                    file=open(tmp_file, 'rb')
                ),
                category=OMRError.STUDENT_NOT_FOUND,
                application=application,
                page_number=page_number,
            )
            continue

        student = Student.objects.filter(
            client__in=omr_upload.user.get_clients(),
            name__icontains=student_name
        )

        if (not student or student.count() > 1):
            OMRError.objects.create(
                upload=omr_upload,
                omr_category=omr_category,
                error_image=UploadedFile(
                    file=open(tmp_file, 'rb')
                ),
                category=OMRError.STUDENT_NOT_FOUND,
                application=application,
                page_number=page_number,
            )
            continue

        if not application:
            OMRError.objects.create(
                upload=omr_upload,
                omr_category=omr_category,
                error_image=UploadedFile(
                    file=open(tmp_file, 'rb')
                ),
                category=OMRError.APPLICATION_NOT_FOUND,
                student=student.first(),
                page_number=page_number,
            )

        if application and student:
            application_student = ApplicationStudent.objects.using("default").filter(
                student=student.first(),
                application=application,
            ).first()

            if not application_student:
                application_student = ApplicationStudent.objects.create(
                    student=student.first(),
                    application=application,
                )

            application_student.is_omr = True
            application_student.save()

            sheet_data['instance'] = str(application_student.pk)

        uploads_data.append(sheet_data)
        os.remove(tmp_file)

    return (upload_id, uploads_data)