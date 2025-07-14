from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from fiscallizeon.omr.models import OMRUpload

class Command(BaseCommand):
    help = 'Marca com status de erro os OMRUpload que estão processando indefinidamente'

    def handle(self, *args, **kwargs):
        uploads = OMRUpload.objects.filter(
            status__in=[OMRUpload.PENDING, OMRUpload.PROCCESSING, OMRUpload.REPROCESSING]
        )

        for upload in uploads:
            if upload.created_at + timedelta(hours=4) < timezone.localtime(timezone.now()):
                print(f"Atualizando upload {upload.pk}")
                upload.status = OMRUpload.ERROR
                upload.save()