import os
import uuid

import urllib

from django.conf import settings
from django.urls import reverse

from fiscallizeon.celery import app
from fiscallizeon.core.print_service import print_to_file
from fiscallizeon.core.storage_backends import PrivateMediaStorage

from fiscallizeon.applications.models import ApplicationStudent

@app.task(max_retries=10, retry_backoff=True, default_retry_delay=2)
def export_custom_page_application_student(application_student_pk, output_dir, blank_pages=False, custom_pages_pks=[]):

    url_params = {
        "application_student": application_student_pk,
        "school_classe": str(ApplicationStudent.objects.get(pk=application_student_pk).get_last_class_student().pk)
    }
    print_url = reverse(
        'exams:custom-pages-print',
    )

    query_string = urllib.parse.urlencode(url_params)
    
    print_url += f'?{query_string}'
    
    for pk in custom_pages_pks:
        print_url += f'&custom_page={pk}'
    

    unique_filename = f'custom_page_{"_".join(custom_pages_pks)}_{str(application_student_pk)}.pdf'
    
    data = {
        "url": settings.BASE_URL + print_url,
        "filename": unique_filename,
        "blank_pages": 'odd' if blank_pages else '',
    }
    
    print(f'Creating custom_page {application_student_pk}')

    tmp_file = os.path.join('tmp', str(uuid.uuid4()))
    print_to_file(tmp_file, data)

    fs = PrivateMediaStorage()
    remote_file = fs.save(
        os.path.join(output_dir, data['filename']),
        open(tmp_file, 'rb')
    )
    os.remove(tmp_file)
    return fs.url(remote_file)