from rest_framework.views import APIView
from rest_framework.response import Response

from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.exports.serializers.application_student_result import ApplicationStudentResultSerializer

class ListExamResults(APIView):
    def get_application_students(self, exam):
        return ApplicationStudent.objects.get_unique_set(
            exam=exam
        )

    def get(self, request, *args, **kwargs):
        teacher = None
        application_students = self.get_application_students(exam=kwargs['exam_id'])
        students_results = application_students.get_annotation_count_answers_filter_teacher(teacher)
        response_body = ApplicationStudentResultSerializer(students_results, many=True)
        return Response(response_body.data)

list_exam_results = ListExamResults.as_view()