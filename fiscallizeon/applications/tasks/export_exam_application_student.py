import os
import uuid
import shutil
import requests
from requests.exceptions import ConnectionError
from urllib3.exceptions import NewConnectionError, ProtocolError

from django.template.defaultfilters import truncatechars

from fiscallizeon.celery import app
from fiscallizeon.core.print_service import print_to_spaces
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.applications.models import ApplicationStudent, ApplicationRandomizationVersion


def create_exam_from_mockup(application_student, output_dir, application_randomization_version=None):
    filename = f'mockup_exam_{application_student.application_id}.html'
    if application_randomization_version:
        filename = f'mockup_exam_{application_student.application_id}_v{application_randomization_version.sequential}.html'

    fs = PrivateMediaStorage()
    remote_path = os.path.join(output_dir, filename)

    tmp_file = f'tmp/{uuid.uuid4()}.html'
    with requests.get(fs.url(remote_path), stream=True) as r:
        with open(tmp_file, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

    with open(tmp_file, 'r') as file:
        html_content = file.read()

    student_school_class = application_student.get_last_class_student()

    html_content = html_content.replace("#NomeDoAluno", application_student.student.name)
    html_content = html_content.replace("#Matricula", application_student.student.enrollment_number)

    if student_school_class:
        html_content = html_content.replace("#Turma", student_school_class.name)
        html_content = html_content.replace("#Unidade", student_school_class.coordination.unity.name)
        html_content = html_content.replace("#Serie", student_school_class.grade.name)
    else:
        html_content = html_content.replace("#Turma", '')
        html_content = html_content.replace("#Serie", '')
        html_content = html_content.replace("#Unidade",'')

    
    with open(tmp_file, 'w') as file:
        file.write(html_content)

    saved_file = fs.save(
        os.path.join(output_dir, f'exam_{application_student.pk}.html'),
        open(tmp_file, 'rb')
    )
    os.remove(tmp_file)
    return fs.url(saved_file)

@app.task(autoretry_for=(Exception,), max_retries=8, retry_backoff=True)
def export_exam_application_student(application_student_pk, output_dir, print_params={}, blank_pages=False, application_randomization_version_pk=None):
    try:
        print(f'Creating exam PDF for {application_student_pk}')
        fs = PrivateMediaStorage()
        application_student = ApplicationStudent.objects.get(pk=application_student_pk)
        
        post_data = {
            "filename": f'exam_{str(application_student_pk)}.pdf',
            "blank_pages": 'odd' if blank_pages else '',
            "check_loaded_element": True,
            "wait_seconds": True,
            "spaces_path": os.path.join(fs.root_path, output_dir)
        }

        if print_params.get('show_footer'):
            post_data['footer_text'] = truncatechars(application_student.application.exam.name, 100)

        if print_params.get('add_page_number') and print_params.get('separate_subjects', 0) == 0:
            post_data['add_page_number'] = True
        
        application_randomization_version = None
        if application_randomization_version_pk:
            application_randomization_version = ApplicationRandomizationVersion.objects.using('default').get(pk=application_randomization_version_pk)
            
        post_data['url'] = create_exam_from_mockup(application_student, output_dir, application_randomization_version)
        return print_to_spaces(post_data)

    except (Exception, ConnectionError, NewConnectionError, ProtocolError, ) as exc:
        print(f'### Error exporting exam for {application_student_pk}: {exc}')