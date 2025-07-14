from decimal import Decimal

from mixer.backend.django import mixer

from fiscallizeon.questions.models import Question
from fiscallizeon.exams.models import Exam, ExamQuestion
from fiscallizeon.answers.models import FileAnswer
from fiscallizeon.applications.models import ApplicationStudent, Application
from fiscallizeon.students.models import Student
from fiscallizeon.clients.models import Client
from fiscallizeon.core.utils import CustomTransactionTestCase


class TestTextualAnswers(CustomTransactionTestCase):
    databases = '__all__'

    def setUp(self):
        self.exam = mixer.blend(Exam, is_abstract=True)
        self.question_1 = mixer.blend(Question, category=Question.TEXTUAL)
        self.question_2 = mixer.blend(Question, category=Question.TEXTUAL)
        self.question_3 = mixer.blend(Question, category=Question.TEXTUAL)

        self.exam_question_1 = mixer.blend(
            ExamQuestion, 
            question=self.question_1, 
            exam=self.exam, 
            weight=1
        )
        self.exam_question_2 = mixer.blend(
            ExamQuestion, 
            question=self.question_2, 
            exam=self.exam, 
            weight=2
        )
        self.exam_question_3 = mixer.blend(
            ExamQuestion, 
            question=self.question_3, 
            exam=self.exam, 
            weight=0
        )

        self.client = mixer.blend(Client)
        self.student = mixer.blend(Student, client=self.client)
        self.application = mixer.blend(Application, exam=self.exam)
        self.application_student = mixer.blend(ApplicationStudent, student=self.student, application=self.application)

    def test_valid_textual_answer(self):
        file_answer_1 = mixer.blend(
            FileAnswer, 
            student_application=self.application_student, 
            question=self.question_1
        )
        file_answer_2 = mixer.blend(
            FileAnswer, 
            student_application=self.application_student, 
            question=self.question_2
        )
        file_answer_3 = mixer.blend(
            FileAnswer, 
            student_application=self.application_student, 
            question=self.question_3
        )

        self.assertIsNotNone(file_answer_1)
        self.assertIsNotNone(file_answer_2)
        self.assertIsNotNone(file_answer_3)

        # Test exam_question 
        self.assertEqual(file_answer_1.exam_question, self.exam_question_1)
        self.assertEqual(file_answer_2.exam_question, self.exam_question_2)
        self.assertEqual(file_answer_3.exam_question, self.exam_question_3)

        #Test teacher_grade
        file_answer_1.teacher_grade = Decimal(0.75)
        file_answer_2.teacher_grade = Decimal(1)
        file_answer_3.teacher_grade = Decimal(2)

        file_answer_1.save()
        file_answer_2.save()
        file_answer_3.save()

        self.assertEqual(file_answer_1.grade, Decimal(0.75))
        self.assertEqual(file_answer_2.grade, Decimal(0.5))
        self.assertEqual(file_answer_3.grade, Decimal(0) or None)