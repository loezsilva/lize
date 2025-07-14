import re
import shutil
from io import BytesIO

import requests
import qrcode
import cv2
from pyzbar import pyzbar

from django.conf import settings

from fiscallizeon.core.gcp.ocr_service import get_ocr_image
from fiscallizeon.core.storage_backends import PrivateMediaStorage


def download_spaces_image(spaces_image_path, destination=None):
    fs = PrivateMediaStorage()

    destination = destination or '/tmp'

    with requests.get(fs.url(spaces_image_path), stream=True) as r:
        tmp_file = f"{destination}/{spaces_image_path.split('/')[-1]}"
        with open(tmp_file, 'wb') as f:
            shutil.copyfileobj(r.raw, f)
        return tmp_file

def get_qr_code(object_id, sequential, operation_type='S'):
    factory = qrcode.image.svg.SvgImage
    qr_content = '{0}:{1}:{2}'.format(
        operation_type,
        sequential,
        str(object_id)
    )
    img = qrcode.make(qr_content, image_factory=factory, box_size=9)
    stream = BytesIO()
    img.save(stream)
    return stream.getvalue().decode()

def _process_qr_image(image):
    qrCodeDetector = cv2.QRCodeDetector()
    decodedText, points, _ = qrCodeDetector.detectAndDecode(image)

    if decodedText:
        return decodedText
    
    if points is None:
        try:
            decoded_info = pyzbar.decode(image)
            return decoded_info[0].data.decode('utf-8') if decoded_info else None   
        except Exception as e:
            print(f"Could not read QR: {e}")

    else:
        y1, y2 = points[0][0][1], points[0][3][1]
        x1, x2 = points[0][0][0], points[0][1][0]

        croped_qr = image[int(y1) - 20:int(y2) + 20, int(x1) - 20:int(x2) + 20 ]
        try:
            decoded_info = pyzbar.decode(croped_qr)
            return decoded_info[0].data.decode('utf-8') if decoded_info else None
        except Exception as e:
            print(f"Could not read QR: {e}")
        
        return None

def process_qr(image):
    try:
        result = _process_qr_image(image)
        if result:
            return result

        croped_image_blured = cv2.GaussianBlur(image, (3,3), 0)
        
        result = _process_qr_image(croped_image_blured)
        if result:
            return result

        (_, croped_image_binarized) = cv2.threshold(croped_image_blured, 127, 255, cv2.THRESH_BINARY)
        result = _process_qr_image(croped_image_binarized)

        if result:
            return result

        croped_image_blured = cv2.GaussianBlur(image, (5,5), 0)
        _, croped_image_blured = cv2.threshold(croped_image_blured, 80, 255, cv2.THRESH_BINARY)
        return _process_qr_image(croped_image_blured)

    except Exception as e:
        print(e)

def process_header_qr(image_path):
    image = cv2.imread(image_path)
    h, w, _ = image.shape
    image_cropped = image[:int(h/4), w-int(w/3):w]
    qr_content = process_qr(image_cropped)
    student_name = None

    if qr_content and len(qr_content) < 10:
        image_cropped = image[:int(h/7), w-int(w/2):w]
        qr_content = process_qr(image_cropped)

    if not qr_content:
        print("UTILIZANDO OCR PARA QR DE PÁGINA")
        crop_img = image[:int(h/6), :w]
        _, buffer = cv2.imencode(".jpg", crop_img)
        io_buf = BytesIO(buffer)
        ocr_json = get_ocr_image(io_buf, file_buffered=True)

        try:
            full_text = ocr_json['responses'][0]['fullTextAnnotation']['text']
            confidence = ocr_json['responses'][0]['fullTextAnnotation']['pages'][0]['confidence']

            if settings.DEBUG:
                print(f'CONFIDENCE: {confidence}')
                print(f'FULL TEXT: {full_text}')

            if confidence > 0.6:
                qr_content_pattern = re.compile("#(.*)#")
                if re_search := qr_content_pattern.search(full_text):
                    try:
                        qr_content = re_search.groups(0)[0]
                        qr_content = qr_content.strip()
                        qr_content = qr_content.replace(' ', '-')
                        qr_content = qr_content.replace('O', '0')
                    except IndexError as e:
                        print(e)
                        qr_content = None
                
                try:
                    student_names = re.findall(r'ALUNO:(.*?)\n', full_text)
                    student_name = student_names[0].strip() if student_names else None
                except Exception as e:
                    student_name = None
                    print(e)

        except Exception as e:
            qr_content = None

    if not qr_content:
        return process_qr(image), student_name
    
    return qr_content, student_name
