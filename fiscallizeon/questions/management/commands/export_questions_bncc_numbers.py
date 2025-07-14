import csv, os, boto3
from django.core.management.base import BaseCommand
from decouple import config
from django.conf import settings
from fiscallizeon.classes.models import Grade
from fiscallizeon.questions.models import Question
from fiscallizeon.bncc.models import Abiliity, Competence


class Command(BaseCommand):
    help = 'Adiciona índice às alternativas de questões objetivas'
   
    def handle(self, *args, **kwargs):
        all_questions = Question.objects.filter(
            coordinations__unity__client__name__icontains="decis"
        ).distinct()

        all_competences = Competence.objects.filter(
            client__isnull=True
        )

        all_abilities = Abiliity.objects.filter(
            client__isnull=True
        )

        grades = Grade.objects.all().order_by('level', 'name').exclude(name__icontains="curso")

        header = ["Nome", "Tipo", "Disciplina"]

        for grade in grades:
            header.append(grade.get_complete_name())

        with open('tmp/bncc_questions_numbers.csv', 'w') as csvfile:
            fieldnames = header

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for abilitie in all_abilities:
                result = {
                    "Nome": abilitie.code if abilitie.code else abilitie.text,
                    "Tipo": "Habilidade",
                    "Disciplina": abilitie.subject.name if abilitie.subject else ""
                }
                for grade in grades:
                    count_questions = all_questions.filter(
                        grade=grade,
                        abilities=abilitie
                    ).distinct().count()
                    result[grade.get_complete_name()] = str(count_questions)

                writer.writerow(result)

            # for comp in all_competences:
            #     comp_name = [comp.code if comp.code else comp.text, "Competência", comp.subject.name if comp.subject else ""]
            #     for grade in grades:
            #         count_questions = all_questions.filter(
            #             grade=grade,
            #             compecentes=comp
            #         ).distinct().count()
            #         comp_name.append(count_questions)
            #     print(", ".join(comp_name))



        session = boto3.session.Session()
        s3 = session.resource(
            's3',
            region_name='nyc3',
            endpoint_url='https://nyc3.digitaloceanspaces.com',
            aws_access_key_id=config('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=config('AWS_SECRET_ACCESS_KEY'),
        )

        path = os.path.join(settings.BASE_DIR, 'tmp/bncc_questions_numbers.csv')
        print(path)
        
        s3.meta.client.upload_file(
            Filename=path,
            Bucket=config('AWS_STORAGE_BUCKET_NAME'),
            Key=f'temp/bncc_questions_numbers.csv'
        )

            