import csv, os, requests, shutil
from decimal import Decimal
from datetime import datetime
from django.db import transaction
from django.core.management.base import BaseCommand
from django.db.models import Q

from fiscallizeon.exams.models import Exam, ExamTeacherSubject
from fiscallizeon.subjects.models import Subject
from fiscallizeon.inspectors.models import Inspector, TeacherSubject
from fiscallizeon.classes.models import Grade

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--path_file', nargs=1, type=str)

    def handle(self, *args, **kwargs):
path_file = "https://fiscallizeremote.nyc3.cdn.digitaloceanspaces.com/temp/caderno_requests_p3.csv"
with requests.get(path_file, stream=True) as r:
    tmp_file = os.path.join("/tmp/exams_requests.csv")
    with open(tmp_file, 'wb') as f:
        shutil.copyfileobj(r.raw, f)
    with open(tmp_file, 'r') as file:
        csvreader = csv.DictReader(file)
        for index_1, row in enumerate(csvreader):
            name = row['nome'].replace("  ", " ").strip()
            exam = Exam.objects.filter(name=name).first()
            exam.save(skip_hooks=True)
            for index in [1,2,3,4,5,6,7,8,9,10,11,12,13]:
                # print(row['nome'])
                # print(row[f'serie_{index}'])
                # print(row[f'disc_{index}'])
                # print(row[f'prof_{index}'])
                # print(row[f'limitar_{index}'])
                # print(row[f'quantidade_{index}'])
                # print(row[f'quant_obj_disc_{index}'])
                # print(row[f'obj_{index}'])
                # print(row[f'quant_disc_{index}'])
                # print(row[f'travar_{index}'])
                # print(row[f'nota_{index}'])
                # print(row[f'obs_{index}'])
                try:
                    grade = row[f'serie_{index}'].replace("  ", " ").strip()
                    subject = row[f'disc_{index}'].replace("  ", " ")
                    teacher = row[f'prof_{index}'].replace("  ", " ").strip()
                    limit_questions = row[f'limitar_{index}'].replace("  ", " ").strip()
                    quantity_questions = row[f'quantidade_{index}'].replace("  ", " ").strip()
                    quantity_obj_disc = row[f'quant_obj_disc_{index}'].replace("  ", " ").strip()
                    quantity_obj = row[f'obj_{index}'].replace("  ", " ").strip()
                    quantity_disc = row[f'quant_disc_{index}'].replace("  ", " ").strip()
                    block = row[f'travar_{index}'].replace("  ", " ").strip()
                    teacher_weight = row[f'nota_{index}'].replace("  ", " ").strip()
                    note = row[f'obs_{index}'].replace("  ", " ").strip()
                    if not subject:
                        continue
                    grade_object = Grade.objects.filter(
                        name__icontains=grade[1],
                        level__in=[
                            Grade.HIGHT_SCHOOL
                        ] if 'm' in grade else [
                            Grade.ELEMENTARY_SCHOOL,
                            Grade.ELEMENTARY_SCHOOL_2
                        ]
                    ).first()
                    subject_name, knowledge_area, segment = subject.split(' - ')
                    subject_object = Subject.objects.filter(
                        Q(

                            Q(client__name__icontains="tamand") |
                            Q(client__isnull=True)
                        ),
                        Q(name__icontains=subject_name),
                        Q(knowledge_area__name__icontains=knowledge_area),
                        Q(knowledge_area__grades__level__in=[
                                Grade.HIGHT_SCHOOL
                            ] if 'médio' in segment.strip().lower() else [
                                Grade.ELEMENTARY_SCHOOL,
                                Grade.ELEMENTARY_SCHOOL_2
                            ]
                        )
                    ).distinct()
                    subject_object = subject_object.first()
                    teacher_object = Inspector.objects.filter(
                        Q(coordinations__unity__client__name__icontains="tamand"),
                        Q(
                            Q(name__icontains=teacher) |
                            Q(email__icontains=teacher)
                        )
                    ).first()
                    teacher_subject = TeacherSubject.objects.filter(
                        teacher=teacher_object,
                        subject=subject_object
                    ).order_by('created_at').last()
                    if not teacher_subject:
                        teacher_subject = TeacherSubject.objects.create(
                            teacher=teacher_object,
                            subject=subject_object,
                            school_year=2024
                        )
                    ExamTeacherSubject.objects.update_or_create(
                        teacher_subject=teacher_subject,
                        exam=exam,
                        quantity=quantity_questions,
                        note=note,
                        order=index,
                        subject_note=Decimal(teacher_weight) if teacher_weight else None,
                        block_subject_note=True if block == "TRUE" else False,
                        block_quantity_limit=True if limit_questions == "TRUE" else False,
                        block_questions_quantity=True if quantity_obj_disc == "TRUE" else False,
                        objective_quantity=quantity_obj if quantity_obj_disc ==  "TRUE" and quantity_obj else 0,
                        discursive_quantity=quantity_disc if quantity_obj_disc ==  "TRUE" and quantity_disc else 0,
                        defaults={
                            'elaboration_email_sent':True,
                            'grade':grade_object,
                        }
                    )
                    print("deu certo")
                except Exception as e:
                    print(e)
                    print("#####",  exam.name, subject, teacher)
