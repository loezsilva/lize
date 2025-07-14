import os, csv, requests, shutil
from django.db import transaction
from urllib.parse import urlparse, parse_qs

from django.conf import settings
from django.core.management.base import BaseCommand

from fiscallizeon.omr.tasks.olimpiada_rio.proccess_sheets_rio import proccess_sheets_rio
    
from fiscallizeon.clients.models import Unity
from fiscallizeon.accounts.models import User
from fiscallizeon.omr.models import OMRCategory, OMRUpload

class Command(BaseCommand):
    help = 'Importa arquivos do RIO'

    def add_arguments(self, parser):
        pass

    def exist_omr(self, file, user):
        return OMRUpload.objects.filter(
            user=user,
            filename=file,
            omr_category=OMRCategory.objects.get(
                sequential=4
            ),
        ).exists()

    def create_omr_object(self, file, user):
        if self.exist_omr(file, user):
            return

        omr_upload = OMRUpload.objects.create(
            user=user,
            filename=file,
            omr_category=OMRCategory.objects.get(
                sequential=4
            ),
        )

        os.makedirs(settings.OMR_UPLOAD_DIR, exist_ok=True)

        destination_path = os.path.join(settings.OMR_UPLOAD_DIR, f'{omr_upload.pk}.pdf')
        shutil.move(file, destination_path)

        proccess_sheets_rio.apply_async(args=[omr_upload.pk])

    def handle(self, *args, **kwargs):
        try:
            os.makedirs('tmp/rio', exist_ok=True)
            session = requests.Session()

            r = session.get("https://rioeduca-my.sharepoint.com/:f:/g/personal/gaddsme_rioeduca_net/Evx8mCygwqFBlc4LTunWLAQBa1kCiQblIk5BGEiZh1pt7g?e=bsCfHZ")

            with open('tmp/rio_files.csv', 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    code = row["code"]
                    name = row["name"]
                    file_1 = row['file_1'].split(";")
                    file_2 = row['file_2'].split(";")
                    file_3 = row['file_3'].split(";")
                    file_4 = row['file_4'].split(";")
                    file_5 = row['file_5'].split(";")

                    raw_files_urls =  file_1+file_2+file_3+file_4+file_5
                    all_files_urls = []

                    for file in raw_files_urls:
                        if not file.strip() == "":
                            all_files_urls.append(file)

                    user = User.objects.filter(
                        username__icontains=f'{code}@'
                    ).first()

                    if not user:
                        print("##### Usuário não encontrado", code)
                        continue

                    for file_url in all_files_urls:
                        try:
                            file_url = file_url.strip()
                            
                            parsed_url = urlparse(file_url)
                            print("parsed_url", parsed_url)
                            captured_value = parse_qs(parsed_url.query)['SourceUrl'][0]
                            print("captured_value", captured_value)
                            file_name = captured_value.split("/")[-1]
                            file_extension = file_name.split(".")[-1]
                            full_path_file = f'tmp/rio/{file_name}'

                            if self.exist_omr(full_path_file, user):
                                continue

                            if file_extension == 'pdf': 
                                if not os.path.isfile(full_path_file):
                                    print("Baixando...", file_name)
                                    with session.get(file_url, stream=True) as r:
                                        tmp_file = os.path.join(full_path_file)
                                        
                                        print("Baixou o arquivo ", file_name)

                                        with open(tmp_file, 'wb') as f:
                                            shutil.copyfileobj(r.raw, f)
                                            self.create_omr_object(full_path_file, user)
                                                
                                else:
                                    self.create_omr_object(full_path_file, user)
                                    print("Arquivo existente:", file_name)
                            else:
                                print("Arquivo não é PDF: ", file_name)
                        except Exception as e:
                            print("Error de dentro", e)

        except Exception as e:
            print("Error de fora", e)

