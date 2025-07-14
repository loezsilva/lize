import os
import sys

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from celery.result import AsyncResult
from djangorestframework_camel_case.parser import CamelCaseFormParser, CamelCaseMultiPartParser
from rest_framework import status
from rest_framework.decorators import api_view, authentication_classes, parser_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from tablib import Dataset

from fiscallizeon.accounts.models import CustomGroup, User
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.clients.models import CoordinationMember, SchoolCoordination, Unity
from fiscallizeon.core.api.csrf_exempt_session import CsrfExemptSessionAuthentication
from fiscallizeon.exports.models import Import
from fiscallizeon.inspectors.models import Inspector as Teacher, TeacherSubject
from fiscallizeon.inspectors.tasks import import_teachers
from fiscallizeon.notifications.models import Notification
from fiscallizeon.students.tasks import import_students
from fiscallizeon.subjects.models import Grade, Subject

from .serializers import ImportCoordinatorSerializer, ImportTeacherSerializer


class NoUnderscoreBeforeNumberCamelCaseFormParser(CamelCaseFormParser):
    json_underscoreize = {'no_underscore_before_number': True}


class NoUnderscoreBeforeNumberCamelCaseMultiPartParser(CamelCaseMultiPartParser):
    json_underscoreize = {'no_underscore_before_number': True}


@login_required
def index(request):
    return render(request, 'onboarding/index.html')


@login_required
def detail(request, step):
    status = request.GET.get('status')
    if status == 'import-teachers-success':
        messages.success(request, 'Importação de professores realizada com sucesso.')

    return render(request, f'onboarding/step-{step}.html')


@login_required
def detail_debug(request, step):
    return render(request, f'onboarding/og-step-{step}.html')


@login_required
def upload_file_coordinators(request, step):
    coordinations = request.user.get_coordinations().distinct()
    if (
        Unity.objects.filter(
            unity_type=Unity.PARENT,
            coordinations__in=request.user.get_coordinations()
        ).exists()
    ):
        coordinations = SchoolCoordination.objects.filter(
            unity__client__in=request.user.get_clients_cache()
        ).distinct()
    classes = SchoolClass.objects.filter(
        coordination__in=request.user.get_coordinations(), school_year=timezone.now().year
    )
    subjects = request.user.get_availables_subjects()

    context = {'coordinations': coordinations, 'classes': classes, 'subjects': subjects}
    return render(request, f'onboarding/step-{step}-coordinators-upload-file.html', context)


@login_required
def upload_file_teachers(request, step):
    coordinations = request.user.get_coordinations().distinct()
    if (
        Unity.objects.filter(
            unity_type=Unity.PARENT,
            coordinations__in=request.user.get_coordinations()
        ).exists()
    ):
        coordinations = SchoolCoordination.objects.filter(
            unity__client__in=request.user.get_clients_cache()
        ).distinct()
    classes = SchoolClass.objects.filter(
        coordination__in=request.user.get_coordinations(), school_year=timezone.now().year
    )
    subjects = request.user.get_availables_subjects()

    context = {'coordinations': coordinations, 'classes': classes, 'subjects': subjects}
    return render(request, f'onboarding/step-{step}-teachers-upload-file.html', context)


@login_required
def upload_file_students(request, step):
    coordinations = request.user.get_coordinations().distinct()
    if (
        Unity.objects.filter(
            unity_type=Unity.PARENT,
            coordinations__in=request.user.get_coordinations()
        ).exists()
    ):
        coordinations = SchoolCoordination.objects.filter(
            unity__client__in=request.user.get_clients_cache()
        ).distinct()
    classes = SchoolClass.objects.filter(
        coordination__in=request.user.get_coordinations(), school_year=timezone.now().year
    )
    subjects = request.user.get_availables_subjects()

    context = {'coordinations': coordinations, 'classes': classes, 'subjects': subjects}
    return render(request, f'onboarding/step-{step}-students-upload-file.html', context)


@login_required
def external_system_students(request, step):
    # return HttpResponse('You are voting on question %s.' % step)
    return render(request, f'onboarding/step-{step}-students-external-system.html')


@login_required
def detail_segments(request, step):
    subjects = request.user.get_availables_subjects()
    subjects_elementary_school = subjects.filter(knowledge_area__grades__level=Grade.ELEMENTARY_SCHOOL)
    subjects_elementary_school_2 = subjects.filter(knowledge_area__grades__level=Grade.ELEMENTARY_SCHOOL_2)
    subjects_hight_school = subjects.filter(knowledge_area__grades__level=Grade.HIGHT_SCHOOL)

    teachers = Teacher.objects.filter(inspector_type=Teacher.TEACHER, coordinations__unity__client__in=request.user.get_clients_cache(), is_inspector_ia=False, user__is_active=True).distinct()
    teachers_elementary_school = teachers.filter(subjects__knowledge_area__grades__level=Grade.ELEMENTARY_SCHOOL)
    teachers_elementary_school_2 = teachers.filter(subjects__knowledge_area__grades__level=Grade.ELEMENTARY_SCHOOL_2)
    teachers_hight_school = teachers.filter(subjects__knowledge_area__grades__level=Grade.HIGHT_SCHOOL)

    classes = SchoolClass.objects.filter(coordination__unity__client__in=request.user.get_clients_cache(), school_year=timezone.now().astimezone().date().year)
    classes_elementary_school = classes.filter(grade__level=Grade.ELEMENTARY_SCHOOL)
    classes_elementary_school_2 = classes.filter(grade__level=Grade.ELEMENTARY_SCHOOL_2)
    classes_hight_school = classes.filter(grade__level=Grade.HIGHT_SCHOOL)

    context = {
        'subjects_elementary_school': subjects_elementary_school,
        'subjects_elementary_school_2': subjects_elementary_school_2,
        'subjects_hight_school': subjects_hight_school,

        'teachers_elementary_school': teachers_elementary_school,
        'teachers_elementary_school_2': teachers_elementary_school_2,
        'teachers_hight_school': teachers_hight_school,

        'classes_elementary_school': classes_elementary_school,
        'classes_elementary_school_2': classes_elementary_school_2,
        'classes_hight_school': classes_hight_school,
    }
    return render(request, f'onboarding/step-{step}.html', context)


@login_required
def define_permissions(request, step):
    groups = CustomGroup.objects.filter(
        Q(client__isnull=True) | Q(client=request.user.client)
    )
    context = {'groups': groups}
    return render(request, f'onboarding/step-{step}.html', context)


@login_required
def feedback(request, step):
    notification = Notification.objects.filter(
        category=Notification.ONBOARDING,
    ).order_by('created_at').last()
    if not notification:
        notification = Notification.objects.create(
            category=Notification.ONBOARDING,
            title='Feedback onboarding',
            description='Feedback do onboarding.',
            start_date=timezone.now(),
            end_date=timezone.now() + timezone.timedelta(days=365*10),
        )
    print(notification.pk)
    context = {'notification': notification}
    return render(request, f'onboarding/step-{step}.html', context)


# @api_view(['POST'])
# @parser_classes((NoUnderscoreBeforeNumberCamelCaseFormParser, NoUnderscoreBeforeNumberCamelCaseMultiPartParser))
# # @csrf_exempt
# @authentication_classes((CsrfExemptSessionAuthentication,))
# def upload_import_students(request):
#     students_spreadsheet_file = request.data.get('students_spreadsheet_file')

#     if not students_spreadsheet_file:
#         return Response({'message': 'File is required.'}, status=400)

#     if not students_spreadsheet_file.name.endswith('.csv') or students_spreadsheet_file.content_type != 'text/csv':
#         return Response({'message': 'Invalid file format. Please upload a CSV file.'}, status=400)

#     filename = default_storage.save(
#         f'tmp/{request.user.client.pk}/imports/students/students_spreadsheet_file.csv',
#         request.data['students_spreadsheet_file']
#     )

#     import_data = Import.objects.create(type='students', created_by=request.user, file_url=filename)

#     task = import_students.delay(request.user.pk, request.user.client.pk, filename)

#     print('###')
#     print(task.id)
#     print('###')

#     return Response({'task_pk': task.id})


# @api_view(['GET'])
# @authentication_classes((CsrfExemptSessionAuthentication,))
# def get_task_status(request, task_pk):
#     task_result = AsyncResult(f'{task_pk}')

#     return Response({
#         "task_pk": task_pk,
#         "task_status": task_result.status,
#         "task_result": task_result.result
#     })


@api_view(['POST'])
@parser_classes((NoUnderscoreBeforeNumberCamelCaseFormParser, NoUnderscoreBeforeNumberCamelCaseMultiPartParser))
# @csrf_exempt
@authentication_classes((CsrfExemptSessionAuthentication,))
def upload_import_coordinators(request):
    serializer = ImportCoordinatorSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    NAME, EMAIL, COORDINATIONS = range(3)
    HEADERS = {
        NAME: 'nome',
        EMAIL: 'email',
        COORDINATIONS: 'coordenacoes',
    }
    dataset = Dataset(
                                #   0       1        2
        headers=HEADERS.values()# ['nome', 'email', 'coordenacoes']
    ).load(serializer.validated_data['file'].read().decode('utf-8'), 'csv')

    coordinators_errors = []
    with transaction.atomic():
        for index, row in enumerate(dataset):
            current_subject = None
            try:
                name, email, coordinations_str = row

                coordinations = []
                if coordinations_str:
                    coordinations = coordinations_str.split(',')

                if not coordinations:
                    raise SchoolCoordination.DoesNotExist

                user = User(
                    email=email,
                    username=email,
                    is_active=True,
                    must_change_password=True,
                )
                user.set_password(email)
                user.save()

                coordinations_obj = SchoolCoordination.objects.filter(pk__in=coordinations)
                CoordinationMember.objects.bulk_create(
                    [
                        CoordinationMember(
                            user=user,
                            coordination=coordination,
                            is_coordinator=True,
                            is_reviewer=True,
                            is_pedagogic_reviewer=True
                        )
                        for coordination in coordinations_obj
                    ]
                )

                if user.client.has_default_groups('coordination'):
                    user.custom_groups.set(user.client.get_groups().filter(client__isnull=False, segment='coordination', default=True))
                else:
                    user.custom_groups.set(user.client.get_groups().filter(client__isnull=True, segment='coordination', default=True))

            except Exception as exception:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print('<B> -----')
                print(exc_type, fname, exc_tb.tb_lineno)
                print(exception)
                type_exception = type(exception)
                print(type_exception)
                print('</B> -----')
                if type_exception == IntegrityError:
                    coordinators_errors.append({'index': index, 'kind': 'email', 'name': row[NAME], 'text': f'O e-mail {row[EMAIL]} já está cadastrado.'})
                elif type_exception == SchoolCoordination.DoesNotExist:
                    message = 'Coordenação não definida.'
                    if row[COORDINATIONS]:
                        message = 'Coordenação não existe.'
                    coordinators_errors.append({'index': index, 'kind': 'coordinations', 'name': row[NAME], 'text': message})
                else:
                    coordinators_errors.append({'index': index, 'kind': 'generic', 'name': row[NAME], 'text': repr(exception)})

                transaction.set_rollback(True)

                return Response({'errors': coordinators_errors}, status=status.HTTP_400_BAD_REQUEST)

    client = request.user.client_uncached # keep this variable because user.client is a property
    client.already_onboarded_coordinators = True
    client.save()

    return Response({'message': 'Ok.', 'errors': coordinators_errors})


@api_view(['POST'])
@parser_classes((NoUnderscoreBeforeNumberCamelCaseFormParser, NoUnderscoreBeforeNumberCamelCaseMultiPartParser))
# @csrf_exempt
@authentication_classes((CsrfExemptSessionAuthentication,))
def upload_import_teachers(request):
    serializer = ImportTeacherSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    # teachers_spreadsheet_file = serializer.validated_data['file']

    # print(teachers_spreadsheet_file)
    # print(teachers_spreadsheet_file.name)
    # print(teachers_spreadsheet_file.content_type)

    # if not teachers_spreadsheet_file:
    #     return Response({'message': 'File is required.'}, status=400)

    # # or teachers_spreadsheet_file.content_type != 'text/csv'
    # if not teachers_spreadsheet_file.name.endswith('.csv'):
    #     return Response({'message': 'Invalid file format. Please upload a CSV file.'}, status=400)

    # filename = default_storage.save(
    #     f'tmp/{request.user.client.pk}/imports/students/teachers_spreadsheet_file.csv',
    #     teachers_spreadsheet_file,
    # )

    # import_data = Import.objects.create(type='teachers', created_by=request.user, file_url=filename)

    # task = import_teachers.delay(
    #     request.user.pk,
    #     request.user.client.pk,
    #     serializer.validated_data['replace_coordinations'],
    #     serializer.validated_data['replace_subjects'],
    #     serializer.validated_data['replace_permissions'],
    #     filename,
    # )

    # print('###')
    # print(task.id)
    # print('###')

    # return Response({'task_pk': task.id})

    NAME, EMAIL, COORDINATION, SUBJECTS, CLASSES, PERMISSIONS = range(6)
    HEADERS = {
        NAME: 'nome',
        EMAIL: 'email',
        COORDINATION: 'coordenacao',
        SUBJECTS: 'disciplinas',
        CLASSES: 'turmas',
        PERMISSIONS: 'permissoes',
    }
    dataset = Dataset(
                                #   0       1        2              3              4         5
        headers=HEADERS.values()# ['nome', 'email', 'coordenacao', 'disciplinas', 'turmas', 'permissoes']
    ).load(
        serializer.validated_data['file'].read().decode('utf-8')
    )

    teachers_errors = []
    with transaction.atomic():
        if serializer.validated_data['replace_coordinations'] or serializer.validated_data['replace_subjects'] or serializer.validated_data['replace_permissions']:
            teachers = Teacher.objects.filter(email__in=[row[EMAIL] for row in dataset])
            # print(teachers)
            for teacher in teachers:
                if serializer.validated_data['replace_coordinations']:
                    teacher.coordinations.set([])
                    # print('teacher.coordinations.set([])')
                if serializer.validated_data['replace_subjects']:
                    TeacherSubject.objects.filter(teacher=teacher, examteachersubject__isnull=True).delete()
                    # print('TeacherSubject.objects.filter...')
                if serializer.validated_data['replace_permissions']:
                    teacher.can_response_wrongs = False
                    teacher.can_elaborate_questions = False
                    teacher.is_discipline_coordinator = False
                    teacher.can_answer_wrongs_others_teachers = False
                    teacher.can_correct_questions_other_teachers = False
                    teacher.has_question_formatter = False
                    teacher.save(skip_hooks=True)
                    # print('teacher.can_response_wrongs = False')

        for index, row in enumerate(dataset):
            current_subject = None
            try:
                name, email, coordination, subjects_str, classes_str, permissions = row
                # print(name)
                # print(email)
                # print(coordination)
                # print(subjects_str)
                # print(classes_str)
                # print(permissions)
                # print('-----')

                if not coordination or not SchoolCoordination.objects.filter(pk=coordination).exists():
                    raise SchoolCoordination.DoesNotExist

                subjects = []
                if subjects_str:
                    subjects = subjects_str.split(',')

                classes = []
                if classes_str:
                    classes = classes_str.split(',')

                teacher, created = Teacher.objects.update_or_create(
                    email=email,
                    defaults={'name': name}
                )
                teacher.coordinations.add(coordination)

                if not teacher.user:
                    teacher.create_user()

                teacher.add_custom_groups()

                if 'coge' in permissions:
                    teacher.can_response_wrongs = True
                if 'elab' in permissions:
                    teacher.can_elaborate_questions = True
                if 'coord' in permissions:
                    teacher.is_discipline_coordinator = True
                if 'cogeo' in permissions:
                    teacher.can_answer_wrongs_others_teachers = True
                if 'cog' in permissions:
                    teacher.can_correct_questions_other_teachers = True
                if 'qf' in permissions:
                    teacher.has_question_formatter = True

                for subject in subjects:
                    current_subject = subject
                    subject_name, knowledge_area, segment = subject.split(' - ')
                    teacher_subject, created = TeacherSubject.objects.get_or_create(
                        teacher=teacher,
                        subject=request.user.get_availables_subjects_cached.get(
                            name__iexact=subject_name, 
                            knowledge_area__name__icontains=knowledge_area,
                            knowledge_area__grades__level__in=[Grade.HIGHT_SCHOOL] if 'médio' in segment.lower() else [Grade.ELEMENTARY_SCHOOL, Grade.ELEMENTARY_SCHOOL_2]
                        ),
                        defaults={'active': True}
                    )

                    for school_class in classes:
                        try:
                            school_class_obj = SchoolClass.objects.get(
                                coordination=SchoolCoordination.objects.get(pk=coordination),
                                name__iexact=school_class.strip(),
                                school_year=timezone.now().year,
                            )
                            teacher_subject.classes.add(school_class_obj)
                        except Exception as exception:
                            print('<A> -----')
                            print(exception)
                            print('</A> -----')
                            type_exception = type(exception)
                            if type_exception == SchoolClass.DoesNotExist:
                                teachers_errors.append({'name': name, 'text': f'Não encontramos a turma {school_class} na coordenação.'})
                            elif type_exception == SchoolCoordination.DoesNotExist:
                                teachers_errors.append({'name': name, 'text': f'Coordenação não encontrada.'})
                            else:
                                teachers_errors.append({'name': name, 'text': f'Erro ao tentar importar o aluno. ({exception})'})

                            transaction.set_rollback(True)

                            return Response({'errors': teachers_errors}, status=status.HTTP_400_BAD_REQUEST)

            except Exception as exception:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print('<B> -----')
                print(exc_type, fname, exc_tb.tb_lineno)
                print(exception)
                type_exception = type(exception)
                print(type_exception)
                print('</B> -----')
                if type_exception == IntegrityError:
                    teachers_errors.append({'index': index, 'kind': 'email', 'name': row[NAME], 'text': f'O e-mail {row[EMAIL]} já está cadastrado.'})
                elif type_exception == Subject.DoesNotExist:
                    teachers_errors.append({'index': index, 'kind': 'subject', 'name': row[NAME], 'text': f'A disciplina {current_subject} não foi encontrada.'})
                elif type_exception == Subject.MultipleObjectsReturned:
                    teachers_errors.append({'index': index, 'kind': 'subject', 'name': row[NAME], 'text': f'Tem mais de uma disciplina com o nome: {current_subject}.'})
                elif type_exception == SchoolCoordination.DoesNotExist:
                    message = 'Coordenação não definida.'
                    if row[COORDINATION]:
                        message = 'Coordenação não existe.'
                    teachers_errors.append({'index': index, 'kind': 'coordination', 'name': row[NAME], 'text': message})
                else:
                    teachers_errors.append({'index': index, 'kind': 'generic', 'name': row[NAME], 'text': repr(exception)})

                transaction.set_rollback(True)

                return Response({'errors': teachers_errors}, status=status.HTTP_400_BAD_REQUEST)

    client = request.user.client_uncached # keep this variable because user.client is a property
    client.already_onboarded_teachers = True
    client.save()

    return Response({'message': 'Ok.', 'errors': teachers_errors})


@api_view(['POST'])
@parser_classes((NoUnderscoreBeforeNumberCamelCaseFormParser, NoUnderscoreBeforeNumberCamelCaseMultiPartParser))
# @csrf_exempt
@authentication_classes((CsrfExemptSessionAuthentication,))
def upload_import_students(request):
    students_errors = []

    client = request.user.client_uncached # keep this variable because user.client is a property
    client.already_onboarded_students = True
    client.save()

    return Response({'message': 'Ok.', 'errors': students_errors})
