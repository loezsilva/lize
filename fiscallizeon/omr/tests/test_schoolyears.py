from django import test
from fiscallizeon.accounts.models import User
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.clients.models import Client

from fiscallizeon.omr.models import OMRUpload, SchoolClass
from fiscallizeon.applications.models import Application
from mixer.backend.django import mixer
from datetime import date

from fiscallizeon.students.models import Student
from fiscallizeon.core.utils import CustomTransactionTestCase


class TestSchoolYear(CustomTransactionTestCase):
    databases = '__all__'

    def setUp(self):
        today = date.today()
        
        self.client = mixer.blend(Client)
        self.user_students = mixer.cycle(5).blend(User)
        self.students = mixer.cycle(5).blend(Student, user=(user for user in self.user_students), client=self.client)
        self.classes = mixer.blend(SchoolClass, students=(student for student in self.students))
        self.application = mixer.blend(Application, date=today, students=(student for student in self.students))
        self.application_students = mixer.cycle(5).blend(ApplicationStudent, application=self.application, student=(student for student in self.students))
        self.upload = mixer.blend(OMRUpload, application=self.application)
        self.upload.application_students.add(*self.application_students)
        self.upload.refresh_from_db()

    def test_get_classes_year(self):
        """
        A função de buscar turmas de um gabarito deve retornar as turmas de um mesmo ano
        """

        classes = self.upload.get_classes

        self.assertIs(classes.exists(), True, "A função retornou um queryset vazio")
