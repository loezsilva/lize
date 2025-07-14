import os
import json
from uuid import UUID
import requests
from requests.exceptions import HTTPError
from django.utils import timezone
from fiscallizeon.core.utils import _get_client_device



from django.conf import settings

def handle_request_orchestrator(url, method="get", params={}, resend=False):
    try:
        full_url = f'{settings.ORCHESTRATOR_BASE_URL}/api/{url}'
        token = f'{os.environ.get("ORCHESTRATOR_TOKEN_TYPE")} {os.environ.get("ORCHESTRATOR_TOKEN")}'
        headers = {
            'Authorization': token,
        }
        
        if method == "get":
            response = requests.get(full_url, params=params, headers=headers)
        elif method == "post":
            response = requests.post(full_url, json=params, headers=headers)
        elif method == "put":
            response = requests.put(full_url, json=params, headers=headers)
        elif method == "patch":
            response = requests.patch(full_url, json=params, headers=headers)
        elif method == "delete":
            response = requests.delete(full_url, headers=headers)

        if response.status_code in [403, 401]:
            if not resend:
                raise HTTPError()
            else:
                raise Exception(response.json())

        return response

    except HTTPError as e:
        full_url = f'{settings.ORCHESTRATOR_BASE_URL}/o/token/'

        response = requests.post(full_url, data={
            'client_id': settings.ORCHESTRATOR_CLIENT_ID,
            'client_secret': settings.ORCHESTRATOR_CLIENT_SECRET,
            'grant_type': 'client_credentials'
        })

        os.environ["ORCHESTRATOR_TOKEN"] = response.json().get('access_token', None)
        os.environ["ORCHESTRATOR_TOKEN_TYPE"] = response.json().get('token_type', None)

        return handle_request_orchestrator(url, method=method, params=params, resend=True)

    except Exception as e:
        raise


def start_application_student(application_student, request):
    application_student.device = _get_client_device(request)

    response_data = {}
    if not application_student.start_time:
        if application_student.can_be_started and application_student.can_be_started_device:
            application_student.browser = request.user_agent.browser.family
            application_student.browser_version = request.user_agent.browser.version_string
            application_student.operation_system = request.user_agent.os.family
            application_student.operation_system_version = request.user_agent.os.version_string
            application_student.device_family = request.user_agent.device.family
            application_student.ip_address = get_client_ip(request)
            application_student.start_time = timezone.now().astimezone()
            application_student.save()

            response_data["device"] = application_student.get_device_display().lower()

            return response_data
            
        else:
            response_data = {}
            response_data['result'] = 'error'
            response_data['message'] = 'Horário não permitido para iniciar aplicação' if not application_student.can_be_started else 'Este tipo dispositivo não é permitido para essa aplicação'

            return response_data
    else:
        response_data["device"] = application_student.get_device_display().lower()
        return response_data


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def convert_uuids(data):
    if isinstance(data, list):
        return [convert_uuids(item) for item in data]
    elif isinstance(data, dict):
        return {
            key: (
                str(value) if isinstance(value, UUID) else 
                convert_uuids(value)
            ) for key, value in data.items()
        }
    return data