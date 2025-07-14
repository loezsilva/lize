from django.conf import settings
from django.db import transaction

from celery import shared_task
from tablib import Dataset

from fiscallizeon.accounts.models import User
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.clients.models import Client, SchoolCoordination
from fiscallizeon.inspectors.models import Inspector as Teacher, TeacherSubject
from fiscallizeon.subjects.models import Grade, Subject

from .students_import import import_students_task


@shared_task()
def import_teachers(
  user_pk,
  client_pk,
  replace_coordinations,
  replace_subjects,
  replace_permissions,
  filename,
):
    print('EXEC TASK import_teachers')
    try:
        path = f'{settings.MEDIA_ROOT}/{filename}'
        print(path)
        with open(path, 'r') as fh:
            print('OPEN FILE')
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
            ).load(fh)

            user = User.objects.get(pk=user_pk)
            client = Client.objects.get(pk=client_pk)

            teachers_errors = []
            if replace_coordinations or replace_subjects or replace_permissions:
                teachers = Teacher.objects.filter(email__in=[row[EMAIL] for row in dataset])
                print(teachers)
                for teacher in teachers:
                    if replace_coordinations:
                        teacher.coordinations.set([])
                        # print('teacher.coordinations.set([])')
                    if replace_subjects:
                        TeacherSubject.objects.filter(teacher=teacher, examteachersubject__isnull=True).delete()
                        # print('TeacherSubject.objects.filter...')
                    if replace_permissions:
                        teacher.can_response_wrongs = False
                        teacher.can_elaborate_questions = False
                        teacher.is_discipline_coordinator = False
                        teacher.can_answer_wrongs_others_teachers = False
                        teacher.can_correct_questions_other_teachers = False
                        teacher.has_question_formatter = False
                        teacher.save(skip_hooks=True)
                        # print('teacher.can_response_wrongs = False')

            for row in dataset:
                print('>>> row')
                with transaction.atomic():
                    print('>>> transaction atomic')
                    current_subject = None
                    try:
                        name, email, coordination, subjects, classes, permissions = row
                        # print(name)
                        # print(email)
                        # print(coordination)
                        # print(subjects)
                        # print(classes)
                        # print(permissions)

                        if not coordination:
                            raise SchoolCoordination.DoesNotExist

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
                                subject=user.get_availables_subjects_cached().get(
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

                                    return Response({'errors': teachers_errors})

                    except Exception as exception:
                        print('<B> -----')
                        print(exception)
                        print('</B> -----')
                        type_exception = type(exception)
                        if type_exception == Subject.DoesNotExist:
                            teachers_errors.append({'name': row[NAME], 'text': f'A disciplina {current_subject} não foi encontrada.'})
                        elif type_exception == Subject.MultipleObjectsReturned:
                            teachers_errors.append({'name': row[NAME], 'text': f'Tem mais de uma disciplina com o nome: {current_subject}.'})
                        elif type_exception == SchoolCoordination.DoesNotExist:
                            teachers_errors.append({'name': row[NAME], 'text': 'Coordenação não definida.'})
                        else:
                            teachers_errors.append({'name': row[NAME], 'text': repr(exception)})

                        transaction.set_rollback(True)

                        return Response({'errors': teachers_errors})

            # client = request.user.client # keep this variable because user.client is a property
            client.already_onboarded_teachers = True
            client.save()

            return Response({'message': 'Ok.', 'errors': teachers_errors})


        return 'Import teachers - Status: <Success> [Ok]'
    except Exception as e:
        return f'Import teachers - Status: <Failure> [{e}]'
