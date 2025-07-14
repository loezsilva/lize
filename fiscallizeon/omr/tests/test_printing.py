import logging

from datetime import datetime, timedelta

from mixer.backend.django import mixer

from django import test
from django.urls import reverse

from fiscallizeon.applications.models import Application, ApplicationStudent
from fiscallizeon.exams.models import Exam
from fiscallizeon.clients.models import CoordinationMember, Client, Unity, SchoolCoordination
from fiscallizeon.accounts.models import User
from fiscallizeon.core.utils import CustomTransactionTestCase

class TestOMRPrinting(CustomTransactionTestCase):
    databases = '__all__'

    def setUp(self):
        logging.disable(logging.CRITICAL)

        admin_user = mixer.blend(
            User, is_admin=True
        )
        client = mixer.blend(Client, has_discursive_answers=True, has_discursive_omr=True)
        
        unity = mixer.blend(
            Unity, 
            client=client,
        )

        coordination = mixer.blend(
            SchoolCoordination,
            unity=unity,
        )

        mixer.blend(
            CoordinationMember, 
            user=admin_user, 
            coordination__unity=unity
        )

        exam = mixer.blend(Exam)
        
        exam.coordinations.add(coordination)

        self.application = mixer.blend(
            Application, 
            date=datetime.now().date() + timedelta(days=1), 
            start='12:00', 
            end='13:00',
            category=Application.PRESENTIAL,
            exam=exam,
        )

        self.application_student = mixer.blend(
            ApplicationStudent,
            application=self.application,
            student__client=mixer.RANDOM,
        )

        self.client = test.Client()
        self.client.force_login(admin_user)

    def test_print_answer_sheet(self):
        url = reverse(
            'omr:print_application_student_answer_sheet',
            kwargs={'pk': self.application_student.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_print_answer_sheet_avulse(self):
        url = reverse(
            'omr:print_detached_answer_sheet',
            kwargs={'pk': self.application.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_print_answer_sheet_discursive(self):
        url = reverse(
            'omr:print_discursive_answer_sheet',
            kwargs={'pk': self.application_student.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_print_answer_sheet_discursive_avulse(self):
        url = reverse(
            'omr:print_detached_discursive_answer_sheet',
            kwargs={'pk': self.application.pk}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def tearDown(self):
        logging.disable(logging.NOTSET)