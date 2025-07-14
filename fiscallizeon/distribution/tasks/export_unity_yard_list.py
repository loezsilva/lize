import os
import uuid
from requests.exceptions import ConnectionError
from urllib3.exceptions import NewConnectionError, ProtocolError

from django.urls import reverse
from django.conf import settings

from fiscallizeon.celery import app
from fiscallizeon.core.print_service import print_to_file
from fiscallizeon.clients.models import Unity
from fiscallizeon.distribution.models import RoomDistribution
from fiscallizeon.core.storage_backends import PrivateMediaStorage


@app.task(autoretry_for=(Exception,), max_retries=8, retry_backoff=True)
def export_unity_yard_list(distribution_pk, unity_pk, output_dir, blank_pages=False):
    """
    Exporta as listas de pátio de um ensalamento para uma unidade
    """
    room_distribution = RoomDistribution.objects.get(pk=distribution_pk)
    unity = Unity.objects.get(pk=unity_pk)

    try:
        print_url = reverse(
            'distribution:distribution_patio_list', 
            kwargs={'pk': room_distribution.pk}
        )

        data = {
            "url": '{}{}?unit={}&hide_dialog=1'.format(
                settings.BASE_URL, 
                print_url,
                unity.pk
            ),
            "filename": f'yard_{unity.pk}.pdf',
            "blank_pages": 'between' if blank_pages else '',
            "check_loaded_element": True,
        }
        
        print(f'Creating yard list for unity {unity.name}')

        tmp_file = os.path.join('tmp', str(uuid.uuid4()))
        print_to_file(tmp_file, data)

        fs = PrivateMediaStorage()
        remote_file = fs.save(
            os.path.join(output_dir, f'yard_{unity.pk}.pdf'),
            open(tmp_file, 'rb')
        )
        os.remove(tmp_file)
        return fs.url(remote_file)

    except (Exception, ConnectionError, NewConnectionError, ProtocolError, ) as e:
        print(f'### Error exporting yard list for unity {unity.name}: {e}')