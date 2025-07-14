from mixer.backend.django import mixer

from django import test 

from fiscallizeon.students.models import Student
from fiscallizeon.classes.models import SchoolClass, Grade
from fiscallizeon.clients.models import SchoolCoordination
from fiscallizeon.core.utils import CustomTransactionTestCase

class TestStudentManager(CustomTransactionTestCase):
    databases = '__all__'

    def setUp(self):
        self.student = mixer.blend(Student, client=mixer.RANDOM)
        self.grade = mixer.blend(Grade)
        self.coordination = mixer.blend(SchoolCoordination)
        self.school_class1 = mixer.blend(SchoolClass)
        self.school_class2 = mixer.blend(SchoolClass, grade=self.grade, coordination=self.coordination)

    def test_student_get_latest_class(self):
        self.school_class1.students.add(self.student)
        self.school_class2.students.add(self.student)

        students = Student.objects.filter(
            pk=self.student.pk
        ).add_last_class()

        self.assertEqual(
            students.first().last_class, 
            self.school_class2.pk
        )

        self.assertEqual(
            students.first().last_class_grade, 
            self.grade.pk
        )

        self.assertEqual(
            students.first().last_class_coordination, 
            self.coordination.pk
        )
