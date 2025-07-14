import os
import shutil
import requests
import cv2
import uuid

from django.core.management.base import BaseCommand
from django.core.files.uploadedfile import UploadedFile

from fiscallizeon.omr.models import OMRUpload, OMRStudents, OMRError
from fiscallizeon.core.storage_backends import PrivateMediaStorage



class Command(BaseCommand):
    help = 'Gira todas as imagens de um upload de OMR para reprocessamento'
    OUTPUT_DIR = 'tmp/split-result'

    def add_arguments(self, parser):
        parser.add_argument('omr_upload_id', nargs='+', type=str)

    def handle(self, *args, **kwargs):
        omr_upload_id = kwargs['omr_upload_id'][0]
        ps = PrivateMediaStorage()

        omr_upload = OMRUpload.objects.get(id=omr_upload_id)
        omr_students = OMRStudents.objects.filter(upload=omr_upload)
        
        for omr_student in omr_students:
            try:
                tmp_file = f"/tmp/{uuid.uuid4()}.jpg"
                with requests.get(omr_student.scan_image.url, stream=True) as r:
                    with open(tmp_file, 'wb') as f:
                        shutil.copyfileobj(r.raw, f)

                
                image = cv2.imread(tmp_file)
                image = cv2.rotate(image, cv2.ROTATE_180)
                cv2.imwrite(tmp_file, image)
                
                ps.delete(omr_student.scan_image.name)
                omr_student.scan_image = UploadedFile(file=open(tmp_file, 'rb'), name=tmp_file)
                omr_student.save()
                print("Student ajustado")

                os.remove(tmp_file)
            except ValueError:
                print("Arquivo não encontrado")

        omr_errors = OMRError.objects.filter(upload=omr_upload, is_solved=False)
        for omr_error in omr_errors:
            tmp_file = f"/tmp/{uuid.uuid4()}.jpg"
            with requests.get(omr_error.error_image.url, stream=True) as r:
                with open(tmp_file, 'wb') as f:
                    shutil.copyfileobj(r.raw, f)
            
            image = cv2.imread(tmp_file)
            image = cv2.rotate(image, cv2.ROTATE_180)
            cv2.imwrite(tmp_file, image)
                
            ps.delete(omr_error.error_image.name)
            omr_error.error_image = UploadedFile(file=open(tmp_file, 'rb'))
            omr_error.save()
            print("Erro ajustado")

            os.remove(tmp_file)

        omr_upload.status = OMRUpload.ERROR
        omr_upload.save()
        print(f'Processo finalizado')