import time

from django.conf import settings

from celery import shared_task

from tablib import Dataset
from import_export import resources

from fiscallizeon.clients.models import SchoolCoordination
from fiscallizeon.exports.models import Import

from .students_import import import_students_task

from ..models import Student


class StudentResource(resources.ModelResource):
    class Meta:
        model = Student
        fields = ("price", "id", "name")


@shared_task()
# def import_students(filename, message):
# def import_students(import_pk):
def import_students(user_pk, client_pk, filename):
    print('EXEC TASK import_students')
    # print('params:')
    # print(f'{user_pk=}')
    # print(f'{client_pk=}')
    # print(f'{filename=}')
    # print(import_pk)
    # print('get data')
    # print(Import.objects.get(pk=import_pk))
    # print('end get data')
    # print('^^^^^^^^^^^^^')
    try:
        # import_data = Import.objects.get(pk=import_pk)
        # print(import_data.file_url)
        # print(f'{settings.MEDIA_ROOT}/{import_data.file_url}')
        # print(filename)
        # print(message)
        # dataset = tablib.Dataset(headers=['id', 'name', 'published'])
        # time.sleep(1*10)

        path = f'{settings.MEDIA_ROOT}/{filename}'
        print(path)
        with open(path, 'r') as fh:
            dataset = Dataset(headers=['nome', 'email', 'usuario', 'senha', 'matricula', 'turmas', 'email_responsavel', 'email_responsavel_2', 'coordenacao_id', 'serie']).load(fh)

            # for row in dataset:
            #     print(row)

            for row in dataset:
                print(row)
                print(client_pk)
                # coordination = SchoolCoordination.objects.get(
                    # pk=row['coordenacao_id'],
                    # unity__client=user.client,
                # ).select_related('unity__client')
                # client = coordination.unity.client

                # print(client.pk)

                # student = Student(
                #     name=row['nome'],
                #     email=row['email'],
                #     # username=row['usuario'],
                #     # password=row['senha'],
                #     enrollment_number=row['matricula'],
                #     # classes=row['turmas'],
                #     responsible_email=row['email_responsavel'],
                #     responsible_email_two=row['email_responsavel_2'],
                #     # coordination_id=row['coordenacao_id'],
                #     # grade=row['serie'],
                #     client=client,
                # )
                # print({
                #     'name': row['nome'],
                #     'email': row['email'],
                #     'enrollment_number': row['matricula'],
                #     'responsible_email': row['email_responsavel'],
                #     'responsible_email_two': row['email_responsavel_2'],
                #     'client': f'{client_pk}',
                # })

            # [Student(name=row['nome'], email=row['email'], username=row['usuario'], password=row['senha'], registration=row['matricula'], classes=row['turmas'], responsible_email=row['email_responsavel'], responsible_email_2=row['email_responsavel_2'], coordination_id=row['coordenacao_id'], grade=row['serie']) for row in dataset]

        # StudentResource().import_data(dataset, raise_errors=True)


        return 'Status: <Success> [Ok]'
    except Exception as e:
        return f'Status: <Failure> [{e}]'
