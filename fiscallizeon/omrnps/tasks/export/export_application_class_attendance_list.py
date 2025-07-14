import os
import urllib

from django.conf import settings
from django.urls import reverse

from fiscallizeon.celery import app
from fiscallizeon.core.print_service import print_to_spaces
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.omrnps.models import ClassApplication

@app.task
def export_application_class_attendance_list(application_class_pk, output_dir):
    try:
        print(f'Creating NPS class attendance list for {application_class_pk}')

        fs = PrivateMediaStorage()
        class_application = ClassApplication.objects.get(pk=application_class_pk)

        post_data = {
            "filename": f'attendance_{str(application_class_pk)}.pdf',
            "check_loaded_element": True,
            "spaces_path": os.path.join(fs.root_path, output_dir)
        }

        print_url = reverse(
            'omrnps:print-class-attendance-list',
            kwargs={'pk': class_application.pk}
        )

        post_data['url'] = settings.BASE_URL + print_url
        return print_to_spaces(post_data)
    
    except IndexError as e:
        print(f'### Error exporting NPS class attendance list for {application_class_pk}: {e}')