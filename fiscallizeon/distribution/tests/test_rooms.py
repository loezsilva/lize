from mixer.backend.django import mixer

from django import test

from fiscallizeon.clients.models import SchoolCoordination
from fiscallizeon.classes.models import SchoolClass, Grade
from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.students.models import Student
from fiscallizeon.distribution.models import Room, RoomDistribution, RoomDistributionStudent
from fiscallizeon.core.utils import CustomTransactionTestCase

class TestRoomsManagers(CustomTransactionTestCase):
    databases = '__all__'
    date = '2021-01-01'
    start = '08:00'
    end = '12:00'

    def setUp(self):
        self.coordination1 = mixer.blend(SchoolCoordination, name='Coordenação 1')
        self.room_distribution1 = mixer.blend(RoomDistribution)

        self.rooms = mixer.cycle(2).blend(
            Room,  
            name=(f'Sala {i} (A)' for i in range(1, 3)),
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
        
        self.students = mixer.cycle(6).blend(Student, name=(f'Aluno {i}' for i in range(1, 7)), client=mixer.RANDOM)
        self.grade1 = mixer.blend(Grade, name='1 ano')
        self.school_class1 = mixer.blend(
            SchoolClass, 
            name='Turma 1', 
            grade=self.grade1,
            coordination=self.coordination1,
        )
        self.school_class1.students.add(*self.students)

        self.application_students = mixer.cycle(6).blend(
            ApplicationStudent, 
            application=self.applications[0], 
            student=(student for student in self.students),
        )

        self.room_distribution_students = mixer.cycle(2).blend(
            RoomDistributionStudent,
            distribution=self.room_distribution1,
            student=(student for student in self.students),
            room=self.rooms[0],
        )

    def test_room_occupation(self):
        rooms = Room.objects.filter(
            pk=self.rooms[0].pk
        ).get_occupation(self.date, self.start, self.end)
        
        # for room in rooms:
        #     self.assertEqual(room.occupation, 2)

    def test_get_first_student_grade_and_class(self):
        rooms = Room.objects.filter(
            pk=self.rooms[0].pk
        ).get_first_student_grade_and_class(
            self.date, self.start, self.end
        )

        students = Student.objects.filter(
            pk__in=[student.pk for student in self.students]
        )

        self.assertEqual(
            rooms[0].first_student_grade,
            students.add_last_class()[0].last_class_grade,
        )

        self.assertEqual(
            rooms[0].first_student_school_class,
            students.add_last_class()[0].last_class,
        )

    def test_get_first_room_distribution(self):
        rooms = Room.objects.filter(
            pk=self.rooms[0].pk
        ).get_first_room_distribution(
            self.date, self.start, self.end
        )

        self.assertEqual(
            rooms[0].first_room_distribution,
            self.room_distribution1.pk
        )