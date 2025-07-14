from mixer.backend.django import mixer
from fiscallizeon.questions.models import Question, QuestionOption
from fiscallizeon.answers.models import SumAnswer, SumAnswerQuestionOption
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.students.models import Student
from fiscallizeon.clients.models import Client
from fiscallizeon.core.utils import CustomTransactionTestCase


class TestSumQuestion(CustomTransactionTestCase):
    databases = '__all__'

    def setUp(self):
        self.question = mixer.blend(Question, category=Question.SUM_QUESTION)
        self.question_option1 = mixer.blend(QuestionOption, question=self.question, is_correct=True, index=1)  #1  -  C
        self.question_option2 = mixer.blend(QuestionOption, question=self.question, is_correct=False, index=2) #2     C
        self.question_option3 = mixer.blend(QuestionOption, question=self.question, is_correct=True, index=3)  #4  -  C
        self.question_option4 = mixer.blend(QuestionOption, question=self.question, is_correct=True, index=4)  #8     E
        self.question_option5 = mixer.blend(QuestionOption, question=self.question, is_correct=False, index=5) #16 -  E
        self.question_option5 = mixer.blend(QuestionOption, question=self.question, is_correct=False, index=6) #32 -  C

        self.client = mixer.blend(Client)
        self.student = mixer.blend(Student, client=self.client)
        self.application_student = mixer.blend(ApplicationStudent, student=self.student)

    def test_valid_sum_question_answer(self):
        """
        Criação de respostas para questão de somatório. Considera-se que o aluno marcou 1, 4 e 16
        """

        sum_answer = mixer.blend(SumAnswer, value=21, student_application=self.application_student, question=self.question)
        self.assertIsNotNone(sum_answer)

        factors = sum_answer.get_factors()
        self.assertListEqual(factors, [1, 4, 16])

        sum_answer.create_sum_option_answers()
        self.assertEqual(sum_answer.sumanswerquestionoption_set.count(), 6)

        sum_answer_options = SumAnswerQuestionOption.objects.filter(sum_answer=sum_answer).order_by('question_option__index')
        self.assertTrue(sum_answer_options[0].checked)
        self.assertFalse(sum_answer_options[1].checked)
        self.assertTrue(sum_answer_options[2].checked)
        self.assertFalse(sum_answer_options[3].checked)
        self.assertTrue(sum_answer_options[4].checked)
        self.assertFalse(sum_answer_options[5].checked)

    def test_invalid_sum_question_answer(self):
        """
        Criação de respostas para questão de somatório com resultado inválido
        """

        sum_answer = mixer.blend(SumAnswer, value=200, student_application=self.application_student, question=self.question)
        sum_answer.create_sum_option_answers()
        
        self.assertEqual(sum_answer.get_factors(), [])
        self.assertTrue(sum_answer.empty)

    def test_grade_sum_question_answer(self):
        """
        Teste do cálculo da nota
        """

        #Número de questões assinaladas incorretamente é maior que as assinaladas corretamente
        sum_answer1 = mixer.blend(SumAnswer, value=23, student_application=self.application_student, question=self.question)
        sum_answer1.create_sum_option_answers()
        
        self.assertEqual(sum_answer1.get_grade_proportion(), 0)

        #Número de questões assinaladas corretamente é maior que as assinaladas incorretamente
        sum_answer2 = mixer.blend(SumAnswer, value=1, student_application=self.application_student, question=self.question)
        sum_answer2.create_sum_option_answers()

        self.assertEqual(sum_answer2.get_grade_proportion(), 0.67)

        #Marcou apenas as respostas corretas
        sum_answer3 = mixer.blend(SumAnswer, value=13, student_application=self.application_student, question=self.question)
        sum_answer3.create_sum_option_answers()

        self.assertEqual(sum_answer3.get_grade_proportion(), 1)