import os
import uuid

import urllib

from django.conf import settings
from django.urls import reverse

from fiscallizeon.celery import app
from fiscallizeon.core.print_service import print_to_file
from fiscallizeon.core.storage_backends import PrivateMediaStorage

@app.task(max_retries=10, retry_backoff=True, default_retry_delay=2)
def export_custom_page_school_classes(school_classe_pk, output_dir, blank_pages=False, custom_pages_pks=[], application_pk=None):
    
    url_params = {
        "school_classe": school_classe_pk,
        "application": application_pk
    }
    
    print_url = reverse(
        'exams:custom-pages-print'
    )

    query_string = urllib.parse.urlencode(url_params)
    
    print_url += f'?{query_string}'

    for pk in custom_pages_pks:
        print_url += f'&custom_page={pk}'
    
    unique_filename = f'custom_page_{"_".join(custom_pages_pks)}_{str(school_classe_pk)}.pdf'
    
    data = {
        "url": settings.BASE_URL + print_url,
        "filename": unique_filename,
        "blank_pages": 'odd' if blank_pages else '',
    }
    
    print(f'Creating custom_page {school_classe_pk}')

    tmp_file = os.path.join('tmp', str(uuid.uuid4()))
    print_to_file(tmp_file, data)

    fs = PrivateMediaStorage()
    remote_file = fs.save(
        os.path.join(output_dir, data['filename']),
        open(tmp_file, 'rb')
    )
    os.remove(tmp_file)
    return fs.url(remote_file)
