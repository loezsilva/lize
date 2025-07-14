import os
import re
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

from django.core.management.base import BaseCommand
from django.core.files.uploadedfile import UploadedFile


from fiscallizeon.questions.models import Question
from fiscallizeon.answers.models import FileAnswer, TextualAnswer
from fiscallizeon.applications.models import ApplicationStudent, Application


class Command(BaseCommand):
    help = 'Cria respostas de anexo para uma aplicação'

    def add_arguments(self, parser):
        parser.add_argument('--application', type=str, help='Application ID')

    def handle(self, *args, **kwargs):
        temp_dir = '/code/tmp/file_answers_temp'
        os.makedirs(temp_dir, exist_ok=True)

        application = Application.objects.get(pk=kwargs['application'])
        application_students = ApplicationStudent.objects.filter(application=application).distinct()

        for application_student in application_students:
            font_path = '/code/fiscallizeon/core/static/administration/assets/fonts/ibm-plex-sans/complete/woff/IBMPlexSans-Regular.woff'
            font = ImageFont.truetype(font_path, size=14)

            text_width, text_height = font.getsize_multiline(application_student.student.name)
            image = Image.new('RGB', (text_width + 30, text_height + 30), color=(255, 255, 255))
            draw = ImageDraw.Draw(image)
            draw.text((10, 10), application_student.student.name, font=font, fill=(0, 0, 0))

            output = BytesIO()
            image.save(output, format='PNG')
            output.seek(0)

            filename = f'{temp_dir}/resposta-{application_student.student.name.replace(" ", "")}.png'
            with open(filename, 'wb') as f:
                f.write(output.read())

            for question in application.exam.questions.filter(category=Question.FILE):
                file_answer = FileAnswer.objects.filter(question=question, student_application=application_student)
                
                if file_answer.exists():
                    continue

                file_answer = FileAnswer.objects.create(
                    question=question,
                    student_application=application_student,
                    arquivo=UploadedFile(
                        file=open(filename, 'rb')
                    )
                )
                print(f"Criando resposta de anexo {file_answer.pk}")
        
            os.remove(filename)