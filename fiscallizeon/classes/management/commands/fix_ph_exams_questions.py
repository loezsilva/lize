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
    help = 'Converte questões discursivas da prova para anexo'

    def handle(self, *args, **kwargs):
        application = Application.objects.get(pk='4a0836e4-4922-43ee-89f2-524bfde61f5c')
        application_students = ApplicationStudent.objects.filter(application=application).distinct()
        for question in application.exam.questions.filter(category=Question.FILE):
            for application_student in application_students:
                file_answer = FileAnswer.objects.filter(question=question, student_application=application_student)
                if file_answer.exists():
                    continue
                
                textual_answer = TextualAnswer.objects.filter(question=question, student_application=application_student)

                if textual_answer.exists():
                    filename = f'tmp/{application_student.pk}/{question.pk}.txt'

                    font_path = '/code/fiscallizeon/core/static/administration/assets/fonts/ibm-plex-sans/complete/woff/IBMPlexSans-Regular.woff'
                    font = ImageFont.truetype(font_path, size=14)

                    text = textual_answer.order_by('created_at').last().content
                    if not text:
                        continue
                    text = re.sub("(.{100})", "\\1\n", text, 0, re.DOTALL)

                    text_width, text_height = font.getsize_multiline(text)
                    image = Image.new('RGB', (text_width + 30, text_height + 30), color=(255, 255, 255))
                    draw = ImageDraw.Draw(image)
                    draw.text((10, 10), text, font=font, fill=(0, 0, 0))

                    output = BytesIO()
                    image.save(output, format='PNG')
                    output.seek(0)

                    filename = f'/code/tmp/resposta-{application_student.student.name.replace(" ", "")}.png'
                    with open(filename, 'wb') as f:
                        f.write(output.read())

                    file_answer = FileAnswer.objects.create(
                        question=question,
                        student_application=application_student,
                        arquivo=UploadedFile(
                            file=open(filename, 'rb')
                        )
                    )

                    print(f"Criando resposta de anexo {file_answer.pk}")
                    os.remove(filename)