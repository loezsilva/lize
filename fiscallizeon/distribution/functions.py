import math

from django.db.models import F, Count, Sum
from django.utils import timezone

from fiscallizeon.applications.models import Application
from fiscallizeon.classes.models import Grade, SchoolClass
from fiscallizeon.students.models import Student
from fiscallizeon.clients.models import SchoolCoordination
from fiscallizeon.distribution.models import RoomDistributionStudent


def distribute_students_coordination(room_distribution, rooms):
    print("Iniciando ensalamento por coordenação")
    distributed_students = []
    students = Student.objects.using('default').filter(
        applicationstudent__application__in=room_distribution.application_set.all(),
        classes__isnull=False,
    ).distinct()

    if room_distribution.shuffle_students:
        students = students.order_by('?')
    else:
        students = students.order_by('name')

    # print("Quantidade de alunos:", students.count())

    applications = Application.objects.filter(
        pk__in=room_distribution.application_set.all().values('pk')
    ).using('default').distinct()

    school_classes = list(
        SchoolClass.objects.using(
            'default'
        ).filter_by_applications(
            applications
        ).values_list('pk', flat=True)
    )

    coordinations = SchoolCoordination.objects.using('default').filter(
        school_classes__in=school_classes,
        school_classes__temporary_class=False,
    ).distinct().order_by('name')

    for coordination in coordinations:
        # print("Coordination:", coordination.name, coordination.pk)
        coordination_students = students.filter_by_coordination(coordination)

        application = room_distribution.application_set.all().using('default').first()

        _rooms = rooms.get_occupation(
            application.date, application.start, application.end
        ).using('default').filter(
            coordination=coordination,
        ).exclude(
            occupation__gte=F('capacity')
        ).distinct().order_by(
            'name', 'coordination', 'occupation'
        )
        
        total_students = coordination_students.count()
        total_capacity = _rooms.aggregate(total_capacity=Sum('capacity')).get('total_capacity')
        
        rooms_occupation = []
        for room in _rooms:
            rooms_occupation.append({
                'instance': room,
                'occupation': room.occupation,
                'capacity': room.capacity,
                'proportion': room.capacity / total_capacity,
            })

        if not _rooms:
            continue

        for student in coordination_students:
            if not rooms_occupation:
                break

            if student.pk in distributed_students:
                continue

            if rooms_occupation[0]['occupation'] == rooms_occupation[0]['capacity']:
                rooms_occupation.pop(0)

            if room_distribution.balance_rooms:
                room_proportion = math.ceil(rooms_occupation[0]['proportion'] * total_students)
                if rooms_occupation[0]['occupation'] > room_proportion and len(rooms_occupation) > 1:
                    rooms_occupation.pop(0)
            
            rooms_occupation[0]['occupation'] += 1
            distributed_students.append(student.pk)

            try:
                RoomDistributionStudent.objects.create(
                    distribution=room_distribution,
                    student=student,
                    room=rooms_occupation[0]['instance'],
                )
            except Exception as e:
                # print(e)
                continue


def distribute_students_grade(room_distribution, rooms):
    print("Iniciando ensalamento por série")
    distributed_students = []
    students = Student.objects.using('default').filter(
        applicationstudent__application__in=room_distribution.application_set.all(),
        classes__isnull=False,
    ).distinct()

    if room_distribution.shuffle_students:
        students = students.order_by('?')
    else:
        students = students.order_by('name')

    # print("Quantidade de alunos:", students.count())

    applications = Application.objects.filter(
        pk__in=room_distribution.application_set.all().values('pk')
    ).using('default').distinct()

    school_classes = SchoolClass.objects.using(
        'default'
    ).filter_by_applications(
        applications
    )
    
    school_class_pks = list(school_classes.values_list('pk', flat=True))

    grades = Grade.objects.using('default').filter(
        schoolclass__in=school_class_pks,
    ).distinct().order_by('name')


    coordinations = SchoolCoordination.objects.using('default').filter(
        school_classes__in=school_class_pks,
        school_classes__temporary_class=False,
    ).distinct().order_by('name')

    for coordination in coordinations:
        # print("Coordination:", coordination.name, coordination.unity.name)
        coordination_students = students.filter_by_coordination(coordination).filter(
            classes__in=school_classes.filter(coordination=coordination),
        )

        # print("Quantidade de alunos da coordenação:", coordination_students.count())

        for grade in grades:
            # print("Grade:", grade.name)
            grade_students = coordination_students.filter_by_grade(grade).using('default')

            # print("Quantidade de alunos da série:", grade_students.count())

            application = room_distribution.application_set.all().using('default').first()

            _rooms = rooms.get_occupation(
                application.date, application.start, application.end
            ).using('default').filter(
                coordination=coordination,
            ).exclude(
                occupation__gte=F('capacity')
            ).distinct().order_by(
                'name', 'coordination', '-occupation'
            )

            rooms_occupation = []
            for room in _rooms:
                room_dict = {
                    'instance': room,
                    'occupation': room.occupation,
                    'capacity': room.capacity,
                    'grade': room.get_last_grade(application.date, application.start, application.end),
                }

                if room_dict['occupation'] == 0 or grade == room_dict['grade']:
                    rooms_occupation.append(room_dict)

            if not _rooms:
                # print("Não há salas disponíveis")
                break

            # print('Quantidade de alunos a serem ensalados:', grade_students.count())
            for student in grade_students:
                if not rooms_occupation:
                    break

                if student.pk in distributed_students:
                    # print(f'Aluno {student} já foi alocado')
                    continue

                if rooms_occupation[0]['occupation'] == rooms_occupation[0]['capacity']:
                    # print("Removendo sala", rooms_occupation[0])
                    rooms_occupation.pop(0)

                if not len(rooms_occupation):
                    # print("Não há salas disponíveis")
                    break
                
                rooms_occupation[0]['occupation'] += 1

                # print(f"Adicionando {student} em {rooms_occupation[0]['instance']}")
                distributed_students.append(student.pk)

                try:
                    RoomDistributionStudent.objects.create(
                        distribution=room_distribution,
                        student=student,
                        room=rooms_occupation[0]['instance'],
                    )
                except Exception as e:
                    # print(e)
                    continue


def distribute_students_by_class(room_distribution, rooms):
    distributed_students = []
    students = Student.objects.using('default').filter(
        applicationstudent__application__in=room_distribution.application_set.all(),
        classes__isnull=False,
        classes__school_year=timezone.now().year,
    ).distinct()

    if room_distribution.shuffle_students:
        students = students.order_by('?')
    else:
        students = students.order_by('name')

    applications = Application.objects.filter(
        pk__in=room_distribution.application_set.all().values('pk')
    ).using('default').distinct()

    school_classes = SchoolClass.objects.using(
        'default'
    ).filter_by_applications(
        applications
    )

    coordinations = SchoolCoordination.objects.using('default').filter(
        school_classes__in=school_classes,
        school_classes__temporary_class=False,
    ).distinct().order_by('name')

    application = room_distribution.application_set.all().using('default').first()

    for coordination in coordinations:
        # print("Coordination:", coordination.name, coordination.unity.name)

        school_classes_coordination = school_classes.filter(
            coordination=coordination,
        ).annotate(
            students_count=Count('students')
        ).distinct().order_by('students_count','name')

        for school_class in school_classes_coordination:
            # print(f"Ensalando turma: {school_class.name}")
            _rooms = rooms.get_occupation(
                application.date, application.start, application.end
            ).using('default').filter(
                coordination=coordination,
            ).exclude(
                occupation__gte=F('capacity')
            ).distinct().order_by(
                'capacity', '-occupation', 'name'
            )

            if not _rooms:
                # print("Não há mais salas disponíveis")
                break

            school_class_students = students.using('default').filter_by_class(school_class)

            rooms_occupation = []
            for room in _rooms:
                room_dict = {
                    'instance': room,
                    'occupation': room.occupation,
                    'capacity': room.capacity,
                    'school_class': room.get_last_class(application.date, application.start, application.end),
                }

                if room_dict['occupation'] == 0 or school_class == room_dict['school_class']:
                    rooms_occupation.append(room_dict)

            for student in school_class_students:
                if not rooms_occupation:
                    break

                if student.pk in distributed_students:
                    # print(f'Aluno {student} já foi alocado')
                    continue

                if rooms_occupation[0]['occupation'] == rooms_occupation[0]['capacity']:
                    rooms_occupation.pop(0)
                
                if not rooms_occupation:
                    # print("Não há mais salas disponíveis")
                    break

                rooms_occupation[0]['occupation'] += 1

                # print(f"Adicionando {student} em {rooms_occupation[0]['instance']}")
                distributed_students.append(student.pk)

                try:
                    RoomDistributionStudent.objects.create(
                        distribution=room_distribution,
                        student=student,
                        room=rooms_occupation[0]['instance'],
                    )
                except Exception as e:
                    # print(e)
                    continue