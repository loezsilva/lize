import os
import uuid
import shutil
import requests

from fiscallizeon.celery import app
from fiscallizeon.core.print_service import print_to_spaces
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.applications.models import ApplicationStudent, ApplicationRandomizationVersion
from fiscallizeon.omr.models import OMRCategory

def create_sheet_from_mockup(application_student, output_dir, omr_category_sequential, application_randomization_version=None):
    filename = f'mockup_essay_answer_sheet_{application_student.application_id}.html'

    fs = PrivateMediaStorage()
    remote_path = os.path.join(output_dir, filename)

    tmp_file = f'tmp/{uuid.uuid4()}.html'
    with requests.get(fs.url(remote_path), stream=True) as r:
        with open(tmp_file, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

    with open(tmp_file, 'r') as file:
        html_content = file.read()

    qr_prefix = f'R{application_randomization_version.version_number}' if application_randomization_version else 'S'
    qr_code_text = f'{qr_prefix}:{omr_category_sequential}:{application_student.pk}'

    student_name_placeholder = f'{application_student.student.name} (Mat. {application_student.student.enrollment_number})'
    html_content = html_content.replace("#NomeDoAluno", student_name_placeholder)
    html_content = html_content.replace("###QR_CONTENT###", qr_code_text)
    
    with open(tmp_file, 'w') as file:
        file.write(html_content)

    saved_file = fs.save(
        os.path.join(output_dir, f'essay_{application_student.pk}.html'),
        open(tmp_file, 'rb')
    )
    os.remove(tmp_file)
    return fs.url(saved_file)

@app.task(max_retries=10, retry_backoff=True, default_retry_delay=2)
def export_application_student_essay_sheet(application_student_pk, output_dir, blank_pages=False, application_randomization_version_pk=None):
    try:
        print(f'Creating essay answer sheet for {application_student_pk}')
        fs = PrivateMediaStorage()
        application_student = ApplicationStudent.objects.get(pk=application_student_pk)

        post_data = {
            "filename": f'essay_{str(application_student_pk)}.pdf',
            "blank_pages": 'between' if blank_pages else '',
            "check_loaded_element": True,
            "spaces_path": os.path.join(fs.root_path, output_dir)
        }

        application_randomization_version = None
        if application_randomization_version_pk:
            application_randomization_version = ApplicationRandomizationVersion.objects.using('default').get(pk=application_randomization_version_pk)

        post_data['url'] = create_sheet_from_mockup(application_student, output_dir, OMRCategory.ESSAY_1, application_randomization_version)
        return print_to_spaces(post_data)

    except Exception as e:
        print(f'### Error exporting essay answer sheet for {application_student_pk}: {e}')