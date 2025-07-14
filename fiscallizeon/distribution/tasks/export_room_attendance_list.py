import os
import uuid
from requests.exceptions import ConnectionError
from urllib3.exceptions import NewConnectionError, ProtocolError

from django.urls import reverse
from django.conf import settings

from fiscallizeon.celery import app
from fiscallizeon.core.print_service import print_to_file
from fiscallizeon.core.storage_backends import PrivateMediaStorage
from fiscallizeon.distribution.models import RoomDistribution, Room


@app.task(autoretry_for=(Exception,), max_retries=8, retry_backoff=True)
def export_room_attendance_list(distribution_pk, room_pk, output_dir, blank_pages=False):
    """
    Exporta a lista de presença de um determinada sala em um ensalamento
    """
    room_distribution = RoomDistribution.objects.get(pk=distribution_pk)
    room = Room.objects.get(pk=room_pk)

    try:        
        print_url = reverse(
            'distribution:room_attendance_detail', 
            kwargs={
                'pk': room.pk,
                'distribution': room_distribution.pk,
            }
        )

        data = {
            "url": '{}{}?hide_dialog=1'.format(settings.BASE_URL, print_url),
            "filename": f'attendance_{room.pk}.pdf',
            "blank_pages": 'between' if blank_pages else '',
        }
        
        print(f'Creating attendance list for room {room.name}')

        tmp_file = os.path.join('tmp', str(uuid.uuid4()))
        print_to_file(tmp_file, data)

        fs = PrivateMediaStorage()
        remote_file = fs.save(
            os.path.join(output_dir, f'attendance_{room.pk}.pdf'),
            open(tmp_file, 'rb')
        )
        os.remove(tmp_file)
        return fs.url(remote_file)

    except (Exception, ConnectionError, NewConnectionError, ProtocolError, ) as e:
        print(f'### Error exporting attendance list for room {room.name}: {e}')
