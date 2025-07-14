import os
import uuid

from django.urls import reverse
from django.conf import settings

from fiscallizeon.celery import app
from fiscallizeon.core.print_service import print_to_file
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.distribution.utils import resize_pdf


@app.task
def export_school_class_attendance_list(application_pk, school_class_pk, output_dir, blank_pages=False):
    """
    Exporta a lista de presença de um determinada turma de uma aplicação
    """
    try:
        print_url = reverse(
            'omr:print_application_attendance_list', 
            kwargs={
                'pk': application_pk,
            }
        ) + f'?school_class={school_class_pk}'

        data = {
            "url": '{}{}'.format(settings.BASE_URL, print_url),
            "filename": f'attendance_{school_class_pk}.pdf',
            "blank_pages": 'between' if blank_pages else '',
            "check_loaded_element": True,
        }
        
        print(f'Creating attendance list for school class {school_class_pk}')

        tmp_file = os.path.join('tmp', str(uuid.uuid4()))
        print_to_file(tmp_file, data)

        # Resizing from A3 to A4
        # resize_pdf(tmp_file, resize_factor=0.71)

        fs = PrivateMediaStorage()
        remote_file = fs.save(
            os.path.join(output_dir, data['filename']),
            open(tmp_file, 'rb')
        )
        os.remove(tmp_file)
        return True

    except Exception as exc:
        print(f'### Error exporting attendance list for {application_pk}')
