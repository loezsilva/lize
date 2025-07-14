import shutil

from pikepdf import Pdf

from django.conf import settings

from fiscallizeon.core.retry import retry
from fiscallizeon.core.requests_utils import get_session_retry
from fiscallizeon.core.gcp.utils import get_service_account_oauth2_token

@retry(tries=6)
def print_to_file(file_name, json_data, local=settings.DEBUG):
    headers = {}
    
    if local:
        print_url = settings.LOCAL_PRINTING_SERVICE_BASE_URL + settings.PRINTING_SERVICE_PATH
    else:
        print_url = settings.PRINTING_SERVICE_BASE_URL + settings.PRINTING_SERVICE_PATH
        try:
            auth_token = get_service_account_oauth2_token(settings.PRINTING_SERVICE_BASE_URL)
            headers = {"Authorization": f"Bearer {auth_token}"}
        except Exception as e:
            print("############# print_to_file >>><<< ", e)

    session = get_session_retry()
    with session.post(print_url, json=json_data, headers=headers, stream=True) as r:
        if r.status_code >= 500:
            raise Exception('HTTP error')
        with open(file_name, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

    try:
        Pdf.open(file_name)
    except:
        raise Exception('Malformed PDF')

    return file_name


@retry(tries=6)
def print_to_spaces(json_data, timeout=300, local=settings.DEBUG):
    
    print_url = settings.PRINTING_SERVICE_BASE_URL + settings.PRINTING_SERVICE_PATH
    headers = {}
    
    if not local:
        try:
            auth_token = get_service_account_oauth2_token(settings.PRINTING_SERVICE_BASE_URL)
            headers = {"Authorization": f"Bearer {auth_token}"}
        except Exception as e:
            print("############# print_to_spaces >>><<< ", e)

    session = get_session_retry()
    response = session.post(print_url, json=json_data, headers=headers, timeout=timeout)

    if not response.status_code == 200:
        print("!!! PDF corrompido ou inexistente")
        raise Exception('Malformed PDF')

    return True