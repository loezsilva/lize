import os
import uuid
import shutil

from django.utils import timezone

from fiscallizeon.celery import app
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.distribution.utils import merge_urls

@app.task
def group_application_students_files(application_students_pk):
    fs = PrivateMediaStorage()
    target_path = os.path.join('ensalamentos', 'tmp', 'avulsos')

    file_path_tmp = os.path.join(
        os.sep, 'code', 'tmp', 'distribution', str(uuid.uuid4())
    )
    os.makedirs(file_path_tmp, exist_ok=True)

    files_path = []
    for application_student_pk in application_students_pk:
        files_path.extend([
            f'answer_{str(application_student_pk)}.pdf',
            f'exam_{str(application_student_pk)}.pdf',
        ])

    final_files_path = [fs.url(os.path.join(target_path, file_path)) for file_path in files_path]
    final_file_name = merge_urls(final_files_path, file_path_tmp)
    
    with open(final_file_name, 'rb') as final_file:
        date_str = timezone.now().strftime('%d-%m-%Y_%H:%M:%S')
        file = fs.save(
            f'{target_path}/malote_individual_{date_str}.pdf',
            final_file
        )

    shutil.rmtree(file_path_tmp)
    return fs.url(file)