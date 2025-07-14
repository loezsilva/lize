import os, csv, requests, shutil, sys
from django.db import transaction
from urllib.parse import urlparse, parse_qs

from django.conf import settings
from django.core.management.base import BaseCommand

from fiscallizeon.omr.tasks.proccess_sheets import proccess_sheets
    
from fiscallizeon.accounts.models import User
from fiscallizeon.omr.models import OMRCategory, OMRUpload
from django.core.files.uploadedfile import UploadedFile


class Command(BaseCommand):
    help = 'Importa arquivos do CURIAR'

    def add_arguments(self, parser):
        pass

    def exist_omr(self, file, user):
        return OMRUpload.objects.filter(
            user=user,
            filename=file,
            omr_category=OMRCategory.objects.get(
                sequential=OMRCategory.FISCALLIZE
            ),
        ).exists()

    def create_omr_object(self, file, user):
        if self.exist_omr(file, user):
            return

        omr_upload = OMRUpload.objects.create(
            user=user,
            filename=file,
            omr_category=OMRCategory.objects.get(
                sequential=OMRCategory.FISCALLIZE
            ),
            raw_pdf=UploadedFile(
                file=open(file, 'rb')
            )
        )

        os.makedirs(settings.OMR_UPLOAD_DIR, exist_ok=True)

        destination_path = os.path.join(settings.OMR_UPLOAD_DIR, f'{omr_upload.pk}.pdf')
        shutil.move(file, destination_path)

        proccess_sheets.apply_async(args=[omr_upload.pk])

    def handle(self, *args, **kwargs):
        try:
            user = User.objects.get(pk='0969afc8-27c3-43d3-99b1-fdbd4edfe945')
            path_file = "https://fiscallizeremote.nyc3.cdn.digitaloceanspaces.com/temp/nomes_outubro.csv"

            with requests.get(path_file, stream=True) as r:
                tmp_file_pdfs = os.path.join("/tmp/arquivos.csv")

                with open(tmp_file_pdfs, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)

                with open(tmp_file_pdfs, 'r') as file:
                    csvreader = csv.DictReader(file)
                    for row in csvreader:
                        file_name = row["arquivo"]
                        file_extension = file_name.split(".")[-1]

                        pdf_file_url = f'https://fiscallizeremote.nyc3.cdn.digitaloceanspaces.com/temp/curiar_out/{file_name}'

                        full_path_file = f'/tmp/curia/{file_name}'

                        if self.exist_omr(full_path_file, user):
                            continue

                        if file_extension == 'pdf':
                            if not os.path.isfile(full_path_file):
                                with requests.get(pdf_file_url, stream=True) as r:
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


                        print(file_name)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno, e)
            print(e)




        #     with open('tmp/rio_files.csv', 'r') as csvfile:
        #         reader = csv.DictReader(csvfile)
        #         for row in reader:
        #             code = row["code"]
        #             name = row["name"]
        #             file_1 = row['file_1'].split(";")
        #             file_2 = row['file_2'].split(";")
        #             file_3 = row['file_3'].split(";")
        #             file_4 = row['file_4'].split(";")
        #             file_5 = row['file_5'].split(";")

        #             raw_files_urls =  file_1+file_2+file_3+file_4+file_5
        #             all_files_urls = []

        #             for file in raw_files_urls:
        #                 if not file.strip() == "":
        #                     all_files_urls.append(file)

        #             user = User.objects.get(pk='0969afc8-27c3-43d3-99b1-fdbd4edfe945')

        #             for file_url in all_files_urls:
        #                 try:
        #                     file_url = file_url.strip()
                            
        #                     parsed_url = urlparse(file_url)
        #                     print("parsed_url", parsed_url)
        #                     captured_value = parse_qs(parsed_url.query)['SourceUrl'][0]
        #                     print("captured_value", captured_value)
        #                     file_name = captured_value.split("/")[-1]
        #                     file_extension = file_name.split(".")[-1]
        #                     full_path_file = f'tmp/rio/{file_name}'

        #                     if self.exist_omr(full_path_file, user):
        #                         continue

        #                     if file_extension == 'pdf': 
        #                         if not os.path.isfile(full_path_file):
        #                             print("Baixando...", file_name)
        #                             with session.get(file_url, stream=True) as r:
        #                                 tmp_file = os.path.join(full_path_file)
                                        
        #                                 print("Baixou o arquivo ", file_name)

        #                                 with open(tmp_file, 'wb') as f:
        #                                     shutil.copyfileobj(r.raw, f)
        #                                     self.create_omr_object(full_path_file, user)
                                                
        #                         else:
        #                             self.create_omr_object(full_path_file, user)
        #                             print("Arquivo existente:", file_name)
        #                     else:
        #                         print("Arquivo não é PDF: ", file_name)
        #                 except Exception as e:
        #                     print("Error de dentro", e)

        # except Exception as e:
        #     print("Error de fora", e)

