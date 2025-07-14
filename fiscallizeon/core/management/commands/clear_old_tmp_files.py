import os
import datetime

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Limpa arquivos e diretórios da pasta tmp'

    TMP_DIR = '/code/tmp'
    KEEP_DIRS = [
        'answer_sheets',
        'distribution',
        'dashboards',
        'persistence',
    ]

    def handle(self, *args, **kwargs):
        now = datetime.datetime.now()

        for root, dirs, files in os.walk(self.TMP_DIR):
            for file in files:
                path = os.path.join(root, file)
                modified_time = datetime.datetime.fromtimestamp(os.path.getmtime(path))
                if (now - modified_time).total_seconds() > 48 * 3600:
                    print(f"Removing file {path}")
                    os.remove(path)

            for dir in dirs:
                path = os.path.join(root, dir)
                if any([x in path for x in self.KEEP_DIRS]):
                    continue

                if not os.listdir(path):
                    print(f"Removing directory {path}")
                    os.rmdir(path)
