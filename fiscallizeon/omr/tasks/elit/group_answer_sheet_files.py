import os
import re
import uuid
import math
import zipfile
import shutil

from django.utils import timezone

from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.clients.models import Unity
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.distribution.utils import merge_urls
from fiscallizeon.celery import app

@app.task
def group_answer_sheet_files(application_pk, export_version):
    application = Application.objects.get(pk=application_pk)
    school_classes = application.get_related_classes()

    unities = Unity.objects.filter(
        pk__in=school_classes.values('coordination__unity')
    )

    exam_name_no_spaces = re.sub(r'[\s]+|/', '_', application.exam.name)
    exam_name_safe = re.sub(r'[^a-zA-Z0-9_]+', '', exam_name_no_spaces)[:64]

    export_tmp_path = os.path.join(
        os.sep, 'code', 'tmp', 'answer_sheets', application_pk, str(export_version)
    )
    os.makedirs(export_tmp_path, exist_ok=True)

    zip_filename = str(uuid.uuid4())[:8]
    
    zip_path = os.path.join(export_tmp_path, f'{zip_filename}_{exam_name_safe}.zip')
    with zipfile.ZipFile(zip_path, "a", zipfile.ZIP_DEFLATED, allowZip64=True) as zip_file:
        base_remote_path = os.path.join(
            'omr', 'exports', application_pk, str(export_version)
        )
        fs = PrivateMediaStorage()

        for unity in unities:
            classes_files = []
            unity_school_classes = SchoolClass.objects.filter(
                coordination__unity=unity,
                pk__in=school_classes.values('pk')
            ).order_by('name')

            for school_class in unity_school_classes:
                classes_files.append(
                    f'attendance_{school_class.pk}.pdf'
                )
                
                application_students_count = ApplicationStudent.objects.filter(
                    application=application
                ).filter_by_school_class(
                    school_class
                ).count()

                class_files_count = math.ceil(application_students_count / 8)
                classes_files.extend(
                    [f'elit_answer_sheet_{school_class.pk}_{i}.pdf' for i in range(class_files_count)]
                )

            unity_name_no_spaces = re.sub(r'[\s]+|/', '_', unity.name)
            unity_name_safe = re.sub(r'[^a-zA-Z0-9_]+', '', unity_name_no_spaces)

            pdf_full_urls = [
                fs.url(os.path.join(base_remote_path, path)) for path in classes_files
            ]

            final_file = merge_urls(pdf_full_urls, export_tmp_path)

            with open(final_file, 'rb') as f:
                zip_file.writestr(f'{unity_name_safe}.pdf', f.read())

    fs = PrivateMediaStorage()
    saved_file = fs.save(
        f'applications/answer_sheets/{application_pk}/{zip_filename}_{exam_name_safe}.zip',
        open(zip_path, 'rb')
    )

    shutil.rmtree(export_tmp_path)

    application.answer_sheet = saved_file
    application.end_last_answer_sheet_generation = timezone.localtime(timezone.now())
    application.sheet_exporting_status = Application.FINISHED
    application.save()