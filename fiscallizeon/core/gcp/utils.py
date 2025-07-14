import os
import tempfile
import json
import datetime

import google.auth.transport.requests
from google.oauth2.id_token import fetch_id_token

from django.conf import settings
from django.core.cache import cache

def _get_service_account_json():
    account_info = {
        "type": "service_account",
        "project_id": settings.GCP_PROJECT_ID,
        "private_key_id": settings.GCP_PRIVATE_KEY_ID,
        "private_key": settings.GCP_PRIVATE_KEY.replace('\\n', '\n'),
        "client_email": settings.GCP_CLIENT_EMAIL,
        "client_id": settings.GCP_CLIENT_ID,
        "auth_uri": settings.GCP_AUTH_URI,
        "token_uri": settings.GCP_TOKEN_URI,
        "auth_provider_x509_cert_url": settings.GCP_AUTH_PROVIDER_X509_CERT_URL,
        "client_x509_cert_url": settings.GCP_CLIENT_X509_CERT_URL
    }

    return account_info


def _get_service_account_oauth2_new_token(target_audience):
    account_info = _get_service_account_json()

    tf = tempfile.NamedTemporaryFile()
    tf.write(json.dumps(account_info).encode('utf-8'))
    tf.seek(0)
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = tf.name

    auth_req = google.auth.transport.requests.Request()
    # token_info = google.oauth2.id_token.verify_oauth2_token(id_token, auth_req)
    # timediff = datetime.datetime.utcfromtimestamp(token_info.get('exp', 0)) - datetime.datetime.now()
    # expiration_seconds = timediff.seconds if timediff.total_seconds() > 0 else 60

    return fetch_id_token(auth_req, target_audience)

def get_service_account_oauth2_token(target_audience):
    cache_key = 'GCP_PRINT_SERVICE_TOKEN'
    if token := cache.get(cache_key):
        return token

    token = _get_service_account_oauth2_new_token(target_audience)
    cache.set(cache_key, token, 600)
    return token