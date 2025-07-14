import os
from io import BytesIO
from urllib.parse import urlparse

import requests
import sentry_sdk
from decouple import config

from fiscallizeon.integrations.models import Integration

def _default_request(path, method, client, body={}):
    integration = Integration.objects.filter(
        client=client,
        erp=Integration.REALMS
    ).first()

    if not integration:
        raise Exception("Cliente não possui integração com REALMS cadastrada")
    
    proxy = {}
    if proxy_server := config('TINYPROXY_URL', default=''):
        proxy['http'] = proxy_server
        proxy['https'] = proxy_server
    
    body['realm'] = integration.school_code

    if method == 'GET':
        response = requests.get(
            url=integration.base_url + path + f'?realm={integration.school_code}',
            headers=integration.headers(),
            proxies=proxy,
        )
    elif method == 'POST':
        response = requests.post(
            url=integration.base_url + path,
            headers=integration.headers(),
            json=body,
            proxies=proxy,
        )
    elif method == 'PUT':
        response = requests.put(
            url=integration.base_url + path,
            headers=integration.headers(),
            json=body,
            proxies=proxy,
        )
    elif method == 'DELETE':
        response = requests.delete(
            url=integration.base_url + path,
            headers=integration.headers(),
            json=body,
            proxies=proxy,
        )
    
    try:
        return response.json()
    except Exception as e:
        sentry_sdk.set_extra('Realms error', response.text)
        sentry_sdk.capture_message(f"Erro na comunicação com API realms")
        return {'errors': response.text}

def get_category(relation_instance):
    path = f'/category/{relation_instance.code}'
    return _default_request(path, 'GET', relation_instance.client)

def create_category(client, body):
    path = '/category'
    return _default_request(path, 'POST', client, body)

def update_category(relation_instance, body):
    path = f'/category/{relation_instance.code}'
    return _default_request(path, 'PUT', relation_instance.client, body)

def delete_category(relation_instance):
    path = f'/category/{relation_instance.code}'
    return _default_request(path, 'DELETE', relation_instance.client)

def create_exam(client, body):
    path = '/task'
    return _default_request(path, 'POST', client, body)

def update_exam(client, exam, body):
    path = f'/task/{exam.id_erp}'
    return _default_request(path, 'PUT', client, body)

def delete_exam(client, exam):
    path = f'/task/{exam.id_erp}'
    return _default_request(path, 'DELETE', client)

def create_questions_batch(client, exam, body):
    path = f'/task/{exam.id_erp}/question/batch'
    return _default_request(path, 'POST', client, body)

def update_questions_batch(client, exam, body):
    path = f'/task/{exam.id_erp}/question/batch'
    return _default_request(path, 'PUT', client, body)

def delete_questions_batch(client, exam, body):
    path = f'/task/{exam.id_erp}/question/batch'
    return _default_request(path, 'DELETE', client, body)

def upload_image(client, image_url):
    path = '/file'

    integration = Integration.objects.filter(
        client=client,
        erp=Integration.REALMS
    ).first()

    if not integration:
        raise Exception("Cliente não possui integração com REALMS cadastrada")

    response = requests.get(image_url)
    response.raise_for_status()
    image_data = BytesIO(response.content)

    proxy = {}
    if proxy_server := config('TINYPROXY_URL', default=''):
        proxy['http'] = proxy_server
        proxy['https'] = proxy_server
    
    data = {'realm': integration.school_code}

    try:
        img_path = urlparse(image_url).path
        basename = os.path.basename(img_path)
        extension = basename.split('.')[1]
    except:
        basename = 'image.jpg'
        extension = 'jpg'

    files = {
        'data': (basename, image_data, f'image/{extension}')
    }

    try:
        response = requests.post(
            url=integration.base_url + path,
            headers=integration.headers(),
            data=data,
            files=files,
            proxies=proxy,
        )

        return response.json()
    except Exception as e:
        print(e)
        sentry_sdk.set_extra('Realms error', response.text)
        sentry_sdk.capture_message(f"Erro na envio da imagem para API realms")
        return {'errors': response.text}