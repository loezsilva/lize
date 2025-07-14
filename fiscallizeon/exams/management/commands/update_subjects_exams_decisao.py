import shutil, csv, os

import requests
from django.core.management.base import BaseCommand

from fiscallizeon.exams.models import Exam
from fiscallizeon.subjects.models import Subject
from fiscallizeon.inspectors.models import TeacherSubject 
from fiscallizeon.classes.models import Grade

class Command(BaseCommand):
    help = 'Atualiza disciplina de cadernos do decisão'

    def add_arguments(self, parser):
        parser.add_argument('--path_file', nargs=1, type=str)

    def handle(self, *args, **kwargs):
        path_file = kwargs['path_file'][0]

grade_dict = {
    "Ensino Médio": [Grade.HIGHT_SCHOOL],
    "Ensino Fundamental": [Grade.ELEMENTARY_SCHOOL, Grade.ELEMENTARY_SCHOOL_2]
}

with requests.get("https://fiscallizeremote.nyc3.cdn.digitaloceanspaces.com/temp/novosajustes.csv", stream=True) as r:
    tmp_file = os.path.join("/tmp/cadernos_decisao.csv")
    print("baixou o arquivo")
    with open(tmp_file, 'wb') as f:
        shutil.copyfileobj(r.raw, f)
        print("copiou")
    with open(tmp_file, 'r') as file:
        csvreader = csv.DictReader(file)
        for index, row in enumerate(csvreader):       
            try:



exam = Exam.objects.filter(
    pk="9ed27421-df63-4b10-b66e-10df9ef3b708"
).distinct()
correct_subject = Subject.objects.filter(
    pk="8613817e-7835-4372-ae64-930d827056cf"
).distinct()
exam_teacher_subjects = exam.first().examteachersubject_set.all().distinct()
# print(exam_teacher_subjects.count())
for exam_teacher_subject in exam_teacher_subjects:
    if exam_teacher_subject.teacher_subject.subject == correct_subject.first():
        continue
    teacher_subject = TeacherSubject.objects.filter(
        teacher=exam_teacher_subject.teacher_subject.teacher,
        subject=correct_subject.first()
    ).order_by('created_at').last()
    if not teacher_subject:
        teacher_subject = TeacherSubject.objects.create(    
            teacher=exam_teacher_subject.teacher_subject.teacher,
            subject=correct_subject.first()
        )
    exam_teacher_subject.teacher_subject = teacher_subject
    exam_teacher_subject.save(skip_hooks=True)