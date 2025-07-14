import base64
import requests

from django.conf import settings


def get_ocr_image(image_file, file_buffered=False):

    if file_buffered:
        image_file.seek(0)
        encoded_string = base64.b64encode(image_file.read())
    else:
        with open(image_file, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read())

    json_data = {
        "requests": [
            {
            "image": {
                "content": encoded_string.decode('utf-8'),
            },
            "features": [
                {
                "type": "DOCUMENT_TEXT_DETECTION"
                }
            ]
            }
        ]
    }

    ocr_url = f"https://vision.googleapis.com/v1/images:annotate?key={settings.GCP_API_KEY}"

    response = requests.post(ocr_url, json=json_data)
    if response.status_code >= 500:
        raise Exception('HTTP error')
    
    return response.json()