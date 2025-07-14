from fiscallizeon.students.models import Student
from fiscallizeon.questions.models import Question
from rest_framework import serializers
from fiscallizeon.applications.models import Application

# Serializers define the API representation.

class CoordinationStudentsWidgetSerializer(serializers.ModelSerializer):

    class Meta:
        model = Student
        fields = ['pk', 'name', ]


class CoordinationQuestionsWidgetSerializer(serializers.ModelSerializer):

    class Meta:
        model = Question
        fields = ['pk', 'category', 'level', ]


class CoordinationApplicationsWidgetSerializer(serializers.ModelSerializer):

    exam = serializers.StringRelatedField(many=False)
    students = serializers.StringRelatedField(many=True)


    class Meta:
        model = Application
        fields = ['pk', 'date', 'exam', 'students', ]

class ExamsSumarySerializer(serializers.Serializer):
    count = serializers.IntegerField()
    elaborating = serializers.IntegerField()
    opened = serializers.IntegerField()
    closed = serializers.IntegerField()
    send_review = serializers.IntegerField()
    text_review = serializers.IntegerField()
    is_printed_count = serializers.IntegerField()
    late = serializers.IntegerField()

class QuestionsSumarySerializer(serializers.Serializer):
    count = serializers.IntegerField()
    approved = serializers.IntegerField()
    reproved = serializers.IntegerField()
    correction_pending = serializers.IntegerField()
    use_later = serializers.IntegerField()
    annuled = serializers.IntegerField()
    lates = serializers.IntegerField()
    opened = serializers.IntegerField()

class ExamQuestionsSumarySerializer(serializers.Serializer):
    exams = ExamsSumarySerializer()
    questions = QuestionsSumarySerializer()
