import logging

from mixer.backend.django import mixer

from fiscallizeon.questions.models import Question
from fiscallizeon.exams.models import Exam
from fiscallizeon.omr.models import OMRCategory
from fiscallizeon.core.utils import CustomTransactionTestCase

class TestOmrTemplateJson(CustomTransactionTestCase):
    """
    Testa se o JSON de leitura de gabarito somatório está sendo gerado corretamente
    """
    databases = '__all__'

    def setUp(self):
        self.exam = mixer.blend(Exam)

        #Choice question
        self.option_question1 = mixer.blend(Question, category=Question.CHOICE)
        self.option_question2 = mixer.blend(Question, category=Question.CHOICE)
        self.option_question3 = mixer.blend(Question, category=Question.CHOICE)
        self.option_question4 = mixer.blend(Question, category=Question.CHOICE)
        self.option_question5 = mixer.blend(Question, category=Question.CHOICE)

        self.exam.questions.add(self.option_question1)
        self.exam.questions.add(self.option_question2)
        self.exam.questions.add(self.option_question3)
        self.exam.questions.add(self.option_question4)
        self.exam.questions.add(self.option_question5)
        
        self.sum_question1 = mixer.blend(Question, category=Question.SUM_QUESTION)
        self.sum_question2 = mixer.blend(Question, category=Question.SUM_QUESTION)
        self.sum_question3 = mixer.blend(Question, category=Question.SUM_QUESTION)

        self.exam.questions.add(self.sum_question1)
        self.exam.questions.add(self.sum_question2)
        self.exam.questions.add(self.sum_question3)


    def test_sum_question_exam_answer_sheet(self):
        """
        Criação de questão de somatório
        """

        self.assertEqual(self.exam.questions.all().count(), 8)

    def tearDown(self):
        pass
        logging.disable(logging.NOTSET)