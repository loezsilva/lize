import os
import uuid
import urllib

import boto3

from django.conf import settings
from django.urls import reverse

from fiscallizeon.core.retry import retry
from fiscallizeon.celery import app
from fiscallizeon.core.print_service import print_to_spaces
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.applications.models import ApplicationStudent, ApplicationRandomizationVersion

def replace_html_content(html_content, application_student, qr_code_text, student_school_class,
                    studant_name, qrcode, unity, class_name):
    student_name_placeholder = f'{application_student.student.name} (Mat. {application_student.student.enrollment_number})'
    html_content = html_content.replace(studant_name, student_name_placeholder)
    html_content = html_content.replace(qrcode, qr_code_text)
    if student_school_class:
        html_content = html_content.replace(class_name, student_school_class.name)
        html_content = html_content.replace(unity, student_school_class.coordination.unity.name)
    else:
        html_content = html_content.replace(unity, '')
        html_content = html_content.replace(class_name, '')

    return html_content

@retry(tries=6)
def create_sheet_from_mockup(
        application_student, output_dir, omr_category_sequential, 
        application_randomization_version=None):
    
    filename = f'mockup_answer_sheet_{application_student.application_id}.html'
    if application_randomization_version:
        filename = f'mockup_answer_sheet_{application_student.application_id}_v{application_randomization_version.sequential}.html'

    fs = PrivateMediaStorage()
    remote_path = os.path.join(fs.location, output_dir, filename)

    tmp_file = f'tmp/{uuid.uuid4()}.html'

    s3 = boto3.session.Session().resource(
        's3', 
        region_name=settings.AWS_REGION_NAME, 
        endpoint_url=settings.AWS_S3_ENDPOINT_URL, 
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID, 
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )

    s3.meta.client.download_file(
        settings.AWS_STORAGE_BUCKET_NAME,
        remote_path,
        tmp_file
    )

    with open(tmp_file, 'r') as file:
        html_content = file.read()

    qr_prefix = f'R{application_randomization_version.version_number}' if application_randomization_version else 'S'
    qr_code_text = f'{qr_prefix}:{omr_category_sequential}:{application_student.pk}'
    student_school_class = application_student.get_last_class_student()

    html_content = replace_html_content(
        html_content,
        application_student,
        qr_code_text,
        student_school_class,
        "#NomeDoAluno",
        "###QR_CONTENT###",
        "#Unidade",
        "#Turma"
    )

    with open(tmp_file, 'w') as file:
        file.write(html_content)

    saved_file = fs.save(
        os.path.join(output_dir, f'answer_{application_student.pk}.html'),
        open(tmp_file, 'rb')
    )
    os.remove(tmp_file)
    return fs.url(saved_file)


@app.task(max_retries=10, retry_backoff=True, default_retry_delay=2)
def export_application_student_answer_sheet(
        application_student_pk, output_dir, sheet_model=None, blank_pages=False, 
        application_randomization_version_pk=None):
    try:
        print(f'Creating answer sheet for {application_student_pk}')
        fs = PrivateMediaStorage()
        application_student = ApplicationStudent.objects.get(pk=application_student_pk)

        post_data = {
            "filename": f'answer_{str(application_student_pk)}.pdf',
            "blank_pages": 'odd' if blank_pages else '',
            "check_loaded_element": True,
            "spaces_path": os.path.join(fs.root_path, output_dir)
        }
        omr_category_sequential = 1
        if sheet_model == 'enem':
            omr_category_sequential = 2
        elif sheet_model == 'hybrid':
            omr_category_sequential = 6
        elif sheet_model == 'sum':
            omr_category_sequential = 11
        elif sheet_model == 'subjects':
            omr_category_sequential = 13
        elif sheet_model == 'reduced':
            omr_category_sequential = 14

        application_randomization_version = None
        if application_randomization_version_pk:
            application_randomization_version = ApplicationRandomizationVersion.objects.using('default').get(pk=application_randomization_version_pk)

        post_data['url'] = create_sheet_from_mockup(
            application_student, output_dir, omr_category_sequential, application_randomization_version)
        return print_to_spaces(post_data)

    except IndexError as e:
        print(f'### Error exporting answer sheet for {application_student_pk}: {e}')