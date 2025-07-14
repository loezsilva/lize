from django import test
from mixer.backend.django import mixer

from fiscallizeon.questions.models import Question, QuestionOption
from fiscallizeon.answers.models import OptionAnswer
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.students.models import Student
from fiscallizeon.clients.models import Client
from fiscallizeon.core.utils import CustomTransactionTestCase


class TestSumQuestion(CustomTransactionTestCase):
    databases = '__all__'

    def setUp(self):
        self.question = mixer.blend(Question, category=Question.SUM_QUESTION)
        self.question_option1 = mixer.blend(QuestionOption, question=self.question, is_correct=True, index=0)
        self.question_option2 = mixer.blend(QuestionOption, question=self.question, is_correct=False, index=1)
        self.question_option3 = mixer.blend(QuestionOption, question=self.question, is_correct=True, index=2)
        self.question_option4 = mixer.blend(QuestionOption, question=self.question, is_correct=False, index=3)
        self.question_option5 = mixer.blend(QuestionOption, question=self.question, is_correct=False, index=4)

        self.client = mixer.blend(Client)
        self.student = mixer.blend(Student, client=self.client)
        self.application_student = mixer.blend(ApplicationStudent, student=self.student)

    def test_sum_question_creation(self):
        """
        Criação de questão de somatório
        """

        self.assertIsNotNone(self.question)
        self.assertIsNotNone(self.question_option1)
        self.assertIsNotNone(self.question_option2)
        self.assertIsNotNone(self.question_option3)
        self.assertIsNotNone(self.question_option4)