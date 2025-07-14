from django.utils import timezone
from rest_framework import serializers

from fiscallizeon.applications.models import ApplicationStudent

class ApplicationStudentResultSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    total_answers = serializers.IntegerField()
    choice_grade_sum = serializers.FloatField()
    textual_grade_sum = serializers.FloatField()
    file_grade_sum = serializers.FloatField()
    sum_questions_grade_sum = serializers.FloatField()
    total_grade = serializers.FloatField()

    class Meta:
        model = ApplicationStudent
        fields = (
            'id', 'application', 'student_name', 'total_answers', 'choice_grade_sum',
            'textual_grade_sum','file_grade_sum', 'sum_questions_grade_sum', 'total_grade'
        )

    def get_student_name(self, instance):
        return instance.student.name