import os

from pdf2image import convert_from_path

from django.core.management.base import BaseCommand
    

class Command(BaseCommand):
    help = 'Separa arquivo PDF em arquivos JPG'
    OUTPUT_DIR = 'tmp/split-result'

    def add_arguments(self, parser):
        parser.add_argument('input_file', nargs='+', type=str)

    def handle(self, *args, **kwargs):       
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        input_file = kwargs['input_file'][0]

        convert_from_path(input_file, output_folder=self.OUTPUT_DIR, fmt="jpg")
        print(f'Arquivo separado na pasta: {self.OUTPUT_DIR}')