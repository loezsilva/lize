import re
import glob
import cv2
import os

from django.core.files.uploadedfile import UploadedFile

from fiscallizeon.celery import app
from fiscallizeon.omr.models import OMRUpload, OMRError
from fiscallizeon.core.gcp.ocr_service import get_ocr_image
from fiscallizeon.students.models import Student

def _crop_student_name(image_path):
    image = cv2.imread(image_path)

    h, w, _ = image.shape
    end_crop_y = int(h/10)
    end_crop_x = int(w-w/4)

    crop_img = image[0:end_crop_y, 0:end_crop_x]
    dirname = os.path.dirname(image_path)
    filename = os.path.basename(image_path)
    final_cropped_filename = os.path.join(dirname, f'cropped_{filename}')
    cv2.imwrite(final_cropped_filename, crop_img)
    return final_cropped_filename

def _get_student(ocr_dict):
    try:
        full_text = ocr_dict['responses'][0]['fullTextAnnotation']['text']
        confidence = ocr_dict['responses'][0]['fullTextAnnotation']['pages'][0]['confidence']

        if confidence < 0.6:
            return None

        name_pattern = re.compile("Aluno\(a\) (.*)\n")
        if not name_pattern.search(full_text):
            return None

        enrollment_pattern = re.compile("[Matrícula|Matricula]\n(\d*)\n")
        if not enrollment_pattern.search(full_text):
            return None

        student_name = name_pattern.search(full_text).groups(0)[0]
        enrollment_number = enrollment_pattern.search(full_text).groups(0)[0]
        students = Student.objects.filter(
            name__icontains=student_name,
            enrollment_number__icontains=enrollment_number,
        )      

        if students.count() == 1:
            return students.first()

        return None

    except IndexError:
        return None

@app.task(bind=True)
def create_omr_errors_eleva(self, upload_id):
    omr_upload = OMRUpload.objects.using('default').get(pk=upload_id)
    omr_files = glob.glob(f'tmp/{upload_id}/*.jpg')

    has_ocr = omr_upload.user.get_clients().filter(enable_omr_ocr=True).exists()

    for index, omr_file in enumerate(sorted(omr_files), 1):
        student = None
        if has_ocr:
            cropped_filename = _crop_student_name(omr_file)
            ocr_dict = get_ocr_image(cropped_filename)
            student = _get_student(ocr_dict)

        OMRError.objects.create(
            upload=omr_upload,
            omr_category=omr_upload.omr_category,
            error_image=UploadedFile(
                file=open(omr_file, 'rb')
            ),
            student=student,
            category=OMRError.STUDENT_NOT_FOUND,
            page_number=index,
        )

    omr_upload.status = OMRUpload.FINISHED
    omr_upload.save()
    self.update_state(state='SUCCESS', meta={'done': omr_upload.total_pages, 'total': omr_upload.total_pages})
    return upload_id