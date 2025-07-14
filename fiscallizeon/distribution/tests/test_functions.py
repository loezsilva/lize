from django import test

from mixer.backend.django import mixer

from fiscallizeon.distribution.models import Room, RoomDistribution, RoomDistributionStudent
from fiscallizeon.distribution.functions import distribute_students_grade, distribute_students_by_class
from fiscallizeon.clients.models import SchoolCoordination
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.students.models import Student
from fiscallizeon.classes.models import SchoolClass, Grade
from fiscallizeon.core.utils import CustomTransactionTestCase


class TestFunctions(CustomTransactionTestCase):
    databases = '__all__'
    date = '2021-01-01'
    start = '08:00'
    end = '12:00'

    def setUp(self):
        self.coordination1 = mixer.blend(SchoolCoordination, name='Coordenação 1', unity=mixer.RANDOM)
        self.room_distribution1 = mixer.blend(RoomDistribution)

        self.rooms = mixer.cycle(4).blend(
            Room,  
            name=(f'Sala {i}' for i in range(1, 5)),
            capacity=5, 
            coordination=self.coordination1,
        )

        self.applications = mixer.cycle(2).blend(
            Application, 
            date=self.date, 
            start=self.start, 
            end=self.end,
            room_distribution=self.room_distribution1,
            category=Application.PRESENTIAL,
        )
        
        #Alunos da aplicação 1
        self.students1 = mixer.cycle(6).blend(Student, client=mixer.RANDOM)
        self.grade1 = mixer.blend(Grade, name='1 ano')
        self.school_class1 = mixer.blend(
            SchoolClass, 
            name='Turma 1', 
            grade=self.grade1,
            coordination=self.coordination1,
        )
        self.school_class1.students.add(*self.students1)

        self.application_students1 = mixer.cycle(6).blend(
            ApplicationStudent, 
            application=self.applications[0], 
            student=(student for student in self.students1),
        )

        #Alunos da aplicação 2
        self.students2 = mixer.cycle(6).blend(Student, client=mixer.RANDOM)
        self.grade2 = mixer.blend(Grade, name='2 ano')
        self.school_class2 = mixer.blend(
            SchoolClass, 
            name='Turma 2',
            grade=self.grade2,
            coordination=self.coordination1,
        )
        self.school_class2.students.add(*self.students2)

        self.application_students2 = mixer.cycle(6).blend(
            ApplicationStudent, 
            application=self.applications[1],
            student=(student for student in self.students2),
        )

    def test_distribute_students_grade(self):
        rooms_pks = [room.pk for room in self.rooms]
        rooms = Room.objects.filter(pk__in=rooms_pks).get_occupation(
            self.date, self.start, self.end
        ).order_by('name')

        room_distribution = RoomDistribution.objects.get(
            pk=self.room_distribution1.pk
        )

        distribute_students_grade(room_distribution, rooms)

        room_distribution_students = RoomDistributionStudent.objects.filter(
            distribution=room_distribution
        )

        #Todos os alunos estão ensalados?
        self.assertEqual(room_distribution_students.count(), len(self.students1) + len(self.students2))

        #Os alunos do primeiro ano estão nas primeiras salas?
        self.assertEqual(
            list(room_distribution_students.filter(student__in=self.students1).order_by('room__name').values_list('room', flat=True).distinct()),
            [room.pk for room in rooms[:2]]
        )

        #Os alunos do segundo ano estão nas últimas salas?
        self.assertEqual(
            list(room_distribution_students.filter(student__in=self.students2).order_by('room__name').values_list('room', flat=True).distinct()),
            [room.pk for room in rooms[2:]]
        )

    def test_distribute_students_school_class(self):
        rooms = Room.objects.filter(
            pk__in=[room.pk for room in self.rooms]
        ).get_occupation(
            self.date, self.start, self.end
        ).order_by('name')

        room_distribution = RoomDistribution.objects.get(
            pk=self.room_distribution1.pk
        )

        #Criando uma sala maior para os alunos do segundo ano
        rooms.filter(name__endswith='3').update(capacity=6)

        distribute_students_by_class(room_distribution, rooms)

        room_distribution_students = RoomDistributionStudent.objects.filter(
            distribution=room_distribution
        )

        #Todos os alunos estão ensalados?
        self.assertEqual(
            room_distribution_students.count(), 
            len(self.students1) + len(self.students2)
        )

        #Os alunos do primeiro ano estão nas primeiras salas?
        # self.assertEqual(
        #     list(room_distribution_students.filter(student__in=self.students1).order_by('room__name').values_list('room', flat=True).distinct()),
        #     [room.pk for room in rooms[:2]]
        # )

        #Os alunos do segundo ano estão na útlima sala?
        # self.assertEqual(
        #     list(room_distribution_students.filter(student__in=self.students2).order_by('room__name').values_list('room', flat=True).distinct()),
        #     [rooms[2].pk]
        # )