import csv
import csv, os, boto3
from decouple import config
from django.conf import settings
from django.db.models import Q
from django.core.management.base import BaseCommand

from fiscallizeon.students.models import Student
from fiscallizeon.questions.models import Question
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.exams.models import Exam, ExamQuestion
from fiscallizeon.applications.models import ApplicationStudent


class Command(BaseCommand):
    help = 'Exporta dados de correções de prova'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **kwargs):

        exams = Exam.objects.filter(
            Q(coordinations__unity__client__name__icontains="decis"),
            Q(name__istartswith="p1_"),
            Q(created_at__year=2024)
        ).distinct()

        exam_name = ""
        class_name = ""
        unity_name = ""
        total_students = 0
        total_student_file_obj = 0
        total_students_file_disc = 0
        total_students_correct_obj = 0
        total_students_correct_disc = 0

        with open('tmp/status-correct-exams.csv', 'w') as csvfile:
            fieldnames = ["prova","turma", "unidade", "total_alunos", "alunos_presentes", "alunos_com_cartao_objetiva", "alunos_com_cartao_discursiva", "total_alunos_com_resp_objetiva", "total_alunos_com_resp_discursiva"]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for exam in exams:
                exam_name = exam.name
                school_classes = SchoolClass.objects.filter(
                    students__in=Student.objects.filter(
                        applicationstudent__application__exam=exam,
                        user__is_active=True
                    ),
                    school_year=2024
                ).distinct()
                for school_class in school_classes:
                    class_name = school_class.name
                    unity_name = school_class.coordination.unity.name
                    students = school_class.students.all().filter(user__is_active=True)
                    application_students = ApplicationStudent.objects.filter(
                        student__in=students,
                        application__exam=exam,
                    ).distinct()
                    application_students_presentes = application_students.filter(
                        Q(
                            Q(omrstudents__scan_image__isnull=False) |
                            Q(omrstudents__omrdiscursivescan__upload_image__isnull=False) |
                            Q(missed=False)
                        )
                    ).distinct()
                    total_students = application_students.count()
                    total_studens_presentes = application_students_presentes.count()
                    total_student_file_obj = application_students_presentes.filter(
                        omrstudents__scan_image__isnull=False
                    ).distinct().count()
                    total_students_file_disc = application_students_presentes.filter(
                        omrstudents__omrdiscursivescan__upload_image__isnull=False
                    ).distinct().count()
                    total_students_correct_obj = application_students_presentes.filter(
                        option_answers__isnull=False
                    ).distinct().count()
                    total_students_correct_disc = application_students_presentes.filter(
                        Q(
                            Q(textual_answers__teacher_grade__isnull=False) |
                            Q(file_answers__teacher_grade__isnull=False)
                        )
                    ).distinct().count()
                    result = {
                        "prova": exam_name,
                        "turma": class_name,
                        "unidade": unity_name,
                        "total_alunos": total_students,
                        "alunos_presentes": total_studens_presentes,
                        "alunos_com_cartao_objetiva": total_student_file_obj,
                        "alunos_com_cartao_discursiva": total_students_file_disc,
                        "total_alunos_com_resp_objetiva": total_students_correct_obj,
                        "total_alunos_com_resp_discursiva": total_students_correct_disc
                    }
                    print(f'{exam_name}, {class_name}, {unity_name}, {total_students}, {total_studens_presentes}, {total_student_file_obj}, {total_students_file_disc}, {total_students_correct_obj}, {total_students_correct_disc}')

                    writer.writerow(result)

        session = boto3.session.Session()
        s3 = session.resource(
            's3',
            region_name='nyc3',
            endpoint_url='https://nyc3.digitaloceanspaces.com',
            aws_access_key_id=config('SPACES_AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=config('SPACES_AWS_SECRET_ACCESS_KEY'),
        )
        path = os.path.join(settings.BASE_DIR, 'tmp/status-correct-exams.csv')
        print(path)
        s3.meta.client.upload_file(
            Filename=path,
            Bucket=config('SPACES_AWS_STORAGE_BUCKET_NAME'),
            Key=f'temp/status-correct-exams.csv'
        )
        