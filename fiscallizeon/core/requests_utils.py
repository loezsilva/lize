import urllib3

import requests
from requests.adapters import HTTPAdapter, Retry

def get_session_retry(retries=5, backoff_factor=0.5):
    session = requests.Session()
    retry = urllib3.Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=frozenset(["POST", "HEAD", "TRACE", "GET", "PUT", "OPTIONS", "DELETE"]),
        raise_on_status=False,
    )
    adapter = requests.adapters.HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session