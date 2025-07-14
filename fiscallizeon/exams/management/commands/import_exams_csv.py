import csv, os, requests, shutil

from django.db import transaction
from django.core.management.base import BaseCommand

from decimal import Decimal
from datetime import datetime

from fiscallizeon.exams.models import Exam
from fiscallizeon.subjects.models import SubjectRelation
from fiscallizeon.clients.models import Client, TeachingStage, EducationSystem, SchoolCoordination

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--path_file', nargs=1, type=str)

    def handle(self, *args, **kwargs):

        
client = Client.objects.filter(name__icontains="tamand").first()
path_file = "https://fiscallizeremote.nyc3.cdn.digitaloceanspaces.com/temp/decisao_p3_cadernos.csv"
with transaction.atomic():
    try:
        with requests.get(path_file, stream=True) as r:
            tmp_file = os.path.join("/tmp/exams.csv")
            with open(tmp_file, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
            with open(tmp_file, 'r') as file:
                csvreader = csv.DictReader(file)
                for index, row in enumerate(csvreader):
                    print(index)
                    year = row['ano'].replace("  ", " ").strip()
                    exam_type = row['tipo'].replace("  ", " ").strip()
                    stage = row['etapa'].replace("  ", " ").strip()
                    system = row['sistema'].replace("  ", " ").strip()
                    name = row['titulo'].replace("  ", " ").strip()
                    grade = row['nota'].replace("  ", " ").strip()
                    start_number = row['numero'].replace("  ", " ").strip()
                    deadline_elaboration = row['elaboracao'].replace("  ", " ").strip()
                    relead_elaboration = row['liberacao'].replace("  ", " ").strip()
                    is_ai = row['anos_iniciais'].replace("  ", " ").strip()
                    is_af = row['anos_finais'].replace("  ", " ").strip()
                    is_em = row['ensino_medio'].replace("  ", " ").strip()
                    position_text_base = row['textos_bases'].replace("  ", " ").strip()
                    related_subjects = row['relacionar'].replace("  ", " ").strip()
                    related_subjects_name = row['disc_relacionadas'].replace("  ", " ").strip()
                    random_alternatives = row['random_alt'].replace("  ", " ").strip()
                    show_ranking = row['ranking'].replace("  ", " ").strip()
                    random_questions = row['random_quest'].replace("  ", " ").strip()
                    allow_teacher_see = row['permitir_professor_ver'].replace("  ", " ").strip()
                    orientation = row['orient'].replace("  ", " ").strip() if row['orient'] else ""
                    exam = Exam.objects.create(
                        correction_by_subject=True if allow_teacher_see == "TRUE" else False,
                        name=name,
                        status=Exam.ELABORATING,
                        random_alternatives=True if random_alternatives == "TRUE" else False,
                        random_questions=True if random_questions == "TRUE" else False,
                        elaboration_deadline=datetime.strptime(deadline_elaboration, "%d/%m/%Y"),
                        release_elaboration_teacher=datetime.strptime(relead_elaboration, "%d/%m/%Y"),
                        category=Exam.EXAM,
                        base_text_location=Exam.PER_QUESTION,
                        start_number=int(start_number) if start_number else 1,
                        total_grade=Decimal(grade) if grade else 10,
                        show_ranking=True if show_ranking == "TRUE" else False,
                        teaching_stage=TeachingStage.objects.filter(
                            client__name__icontains="tamand",
                            name=stage
                        ).first(),
                        education_system=EducationSystem.objects.filter(
                            client__name__icontains="tamand",
                            name=system
                        ).first(),
                        orientations="" or orientation, 
                        related_subjects=True if related_subjects == "TRUE" else False
                    )
                    coordinations = SchoolCoordination.objects.filter(
                            unity__client__name__icontains="tamand",
                            high_school = True if is_em == "TRUE" else False,
                            elementary_school = True if is_ai == "TRUE" else False,
                            elementary_school2 = True if is_af == "TRUE" else False
                        )
                    exam.coordinations.set(
                        coordinations
                    )
                    if related_subjects_name:
                        relations = SubjectRelation.objects.filter(
                                client__name__icontains="tamand",
                                name=related_subjects_name
                            )
                        print(relations)
                        exam.relations.set(
                            relations
                        )
    except Exception as e:
        print(e)

