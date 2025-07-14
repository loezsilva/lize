from rest_framework.authentication import BasicAuthentication 
from rest_framework.generics import RetrieveAPIView
from rest_framework.mixins import UpdateModelMixin
from rest_framework.generics import ListAPIView, GenericAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication

from django.db.models import Max
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin

from fiscallizeon.exams.models import Exam
from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.exams.serializers.exam_questions import ExamQuestionAnswersSerializer, ExamQuestionAnswersV2Serializer
from fiscallizeon.exams.serializers.exams import ExamQuestionSerializer
from fiscallizeon.exams.models import ExamQuestion, Question
from fiscallizeon.exams.permissions import IsCoordinationExamQuestion, IsTeacherSubjectExamQuestion
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.core.api import CsrfExemptSessionAuthentication

class ExamQuestionAnswersView(RetrieveAPIView):
    serializer_class = ExamQuestionAnswersSerializer
    model = ExamQuestion
    queryset = ExamQuestion.objects.all()
    permission_classes = [IsCoordinationExamQuestion|IsTeacherSubjectExamQuestion]
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    
class ExamQuestionAnswersV2View(RetrieveAPIView):
    serializer_class = ExamQuestionAnswersV2Serializer
    model = ExamQuestion
    queryset = ExamQuestion.objects.all()
    permission_classes = [IsCoordinationExamQuestion|IsTeacherSubjectExamQuestion]
    authentication_classes = (CsrfExemptSessionAuthentication, )


class ExamQuestionPartialUpdateView(GenericAPIView, UpdateModelMixin):
    queryset = ExamQuestion.objects.all()
    serializer_class = ExamQuestionSerializer
    permission_classes = [IsCoordinationExamQuestion|IsTeacherSubjectExamQuestion]
    authentication_classes = (CsrfExemptSessionAuthentication, )

    def put(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)
from fiscallizeon.answers.models import (
    OptionAnswer, FileAnswer, TextualAnswer, RetryAnswer, SumAnswer, SumAnswerQuestionOption
)
class ExamQuestionEssayGradeAPIView(LoginRequiredMixin, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, TokenAuthentication, )
    
    def post(self, request):
        data = request.data
        exam_ids = data.get('exams', [])
        student_ids = data.get('students', [])
        year = data.get('year', None)

        if not exam_ids or not student_ids or not year:
            return Response({"detail": "Exams, students, and year are required."}, status=status.HTTP_400_BAD_REQUEST)

        exams = Exam.objects.filter(id__in=exam_ids)

        if not exams.exists():
            return Response({"detail": "No exams found for the given IDs."}, status=status.HTTP_404_NOT_FOUND)
        
        student_grades = self._calculate_student_grades(student_ids, exams)

        essay_grades = [{'student_id': student_id, 'max_grade': grade} for student_id, grade in student_grades.items()]
        return Response({"essay_grades": list(essay_grades)}, status=status.HTTP_200_OK)
    
    def _calculate_student_grades(self, student_ids, exams):
        grade = 0
        student_grades = {student_id: 0 for student_id in student_ids}
        for student_id in student_ids:

            application_students = ApplicationStudent.objects.filter(student__id=student_id, application__exam__in=exams)

            for application_student in application_students:
                exam_essays = ExamQuestion.objects.filter(
                    exam=application_student.application.exam,
                    question__is_essay=True,
                )

                for exam_question in exam_essays:
                    grade = self._get_teacher_essay_grade(exam_question, application_student)

            student_grades[student_id] = grade

        return student_grades
    
    def _get_teacher_essay_grade(self, exam_question, application_student):
        active_answers = self._get_file_and_textual_answer(application_student, exam_question.question)
        score = 0
        
        if active_answers:
            active_answer = active_answers[0]
            if active_answer.teacher_grade:
                score = active_answer.teacher_grade

        return score
    
    def _get_file_and_textual_answer(self, application_student, question):
        if question.category == Question.TEXTUAL:
            return TextualAnswer.objects.filter(
                question=question,
                student_application=application_student,
            )
        elif question.category == Question.FILE:
            return FileAnswer.objects.filter(
                question=question,
                student_application=application_student,
            )

        return None


        
exam_question_essay_grade = ExamQuestionEssayGradeAPIView.as_view()
exam_question_partial_update = ExamQuestionPartialUpdateView.as_view()
exam_question_answers_detail = ExamQuestionAnswersView.as_view()
exam_question_answers_detail_v2 = ExamQuestionAnswersV2View.as_view()
