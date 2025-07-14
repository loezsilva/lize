import requests
import pandas as pd

from django.core.management.base import BaseCommand
from django.conf import settings

from fiscallizeon.exams.models import Exam
from fiscallizeon.students.models import Student
from fiscallizeon.answers.models import OptionAnswer
from fiscallizeon.core.gcp.utils import get_service_account_oauth2_token

class Command(BaseCommand):
    help = 'Command para gerar performance de dados agrupados das provas.'

    def handle(self, *args, **kwargs):
        auth_token = get_service_account_oauth2_token(settings.ANALYTICS_SERVICE_URL)
        headers = {"Authorization": f"Bearer {auth_token}"}

        areas_names = {
            'cbafbbba-323e-4e46-be76-abcb5c537490': 'CN',
            'b9eceae4-855a-40f9-9f5e-aa8c942485b2': 'CH',
            '990d414c-ebd1-49f1-a185-005c229178d5': 'MT',
            '41c911a2-9597-4c8f-8e8f-178749fc11db': 'LC',
        }

        exams = Exam.objects.filter(pk__in=[
            '7570d34d-754b-4155-85a4-26b7a4875191',
            '49762fc0-ae06-460b-81d8-0da7bfa45b33',
            '547e6c06-7cd1-41a9-8bed-edfebe0ba24c',
            '782caacf-5841-4ef4-94d7-a438e76b4e00',
            '6ad99737-823a-4e0d-bf7b-0358cff24572',
            '5514337e-cbf0-4c3e-aef4-7ef8638fd1fb',
            '0744e1be-ffe5-4d41-856d-7c5e58ad424d',
            '6c6d7b15-a732-4afd-b750-97c3facf9bbe', 
        ])

        students_data = []
        for exam in exams:
            print(f'Exportando prova {exam} - {exam.pk}')
            answers_count = OptionAnswer.objects.filter(
                student_application__application__exam=exam,
                status=OptionAnswer.ACTIVE
            ).count()

            if not answers_count:
                print(f'Prova {exam} sem respostas')
                continue

            request_data = {
                "year": 2023,
                "exams": [str(exam.pk)],
            }

            response = requests.post(
                settings.ANALYTICS_SERVICE_URL + '/tri',
                headers=headers,
                json=request_data
            )

            for student in response.json()['students']:
                school_class = Student.objects.get(pk=student['student_id']).get_last_class().name

                for knowledge_area in student['knowledge_areas']:
                    students_data.append({
                        'aluno': student['student_name'],
                        'turma': school_class,
                        'caderno': exam.name,
                        'area': areas_names[knowledge_area['id']],
                        'nota': knowledge_area['grade'],
                    })
                

        students_df = pd.DataFrame(students_data).set_index('aluno')
        students_df.to_csv('tmp/notas_tri-com-lize.csv')
        print(students_df)