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
    start_crop_y = int(2*h/9.5)
    end_crop_y = int(start_crop_y+h/14.5)

    crop_img = image[start_crop_y:end_crop_y, 0:w]

    dirname = os.path.dirname(image_path)
    filename = os.path.basename(image_path)
    final_cropped_filename = os.path.join(dirname, f'cropped_{filename}')
    cv2.imwrite(final_cropped_filename, crop_img)
    return final_cropped_filename

def _get_application_student(ocr_dict):
    try:
        full_text = ocr_dict['responses'][0]['fullTextAnnotation']['text']
        confidence = ocr_dict['responses'][0]['fullTextAnnotation']['pages'][0]['confidence']

        if confidence < 0.6:
            return None

        print(full_text)

        students = Student.objects.filter(name__icontains=full_text)

        if students.count() == 1:
            #Cria o application student
            pass

    except IndexError:
        return None

@app.task(bind=True)
def create_omr_errors_rio(self, upload_id):
    omr_upload = OMRUpload.objects.using('default').get(pk=upload_id)
    omr_files = glob.glob(f'tmp/{upload_id}/*.jpg')

    for index, omr_file in enumerate(sorted(omr_files), 1):
        # Quando for utilizar OCR
        # cropped_filename = _crop_student_name(omr_file)
        # ocr_dict = get_ocr_image(cropped_filename)
        # application_student = _get_application_student(ocr_dict)

        OMRError.objects.create(
            upload=omr_upload,
            omr_category=omr_upload.omr_category,
            error_image=UploadedFile(
                file=open(omr_file, 'rb')
            ),
            category=OMRError.STUDENT_NOT_FOUND,
            page_number=index,
        )

    omr_upload.status = OMRUpload.FINISHED
    omr_upload.save()
    self.update_state(state='SUCCESS', meta={'done': omr_upload.total_pages, 'total': omr_upload.total_pages})
    return upload_id