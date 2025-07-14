from django.conf import settings
from django.core.management.base import BaseCommand

from fiscallizeon.omr.models import OMRUpload
import time
from django.db.models import Q

class Command(BaseCommand):
    help = 'Remove os já corrigidos da listagem'

    def add_arguments(self, parser):
        client_pk = parser.add_argument('--client_pk')


    def handle(self, *args, **kwargs):
        try:
            uploads = OMRUpload.objects.filter(
                Q(
                    Q(corrected=False) | Q(seen=False)
                ),
                Q(user__coordination_member__coordination__unity__client=kwargs['client_pk'])
            ).order_by('-created_at').distinct()
            
            print(uploads.count(), "Uploads não corrigidos.")
            
            start = time.time()
            
            for upload in uploads:
                if not upload.student_page_error_count:
                    upload.corrected = True
                    upload.seen = True
                    upload.save(skip_hooks=True)
            
            print("Terminou: ", time.time() - start)
            
        except Exception as e:
            print("except: ", e)