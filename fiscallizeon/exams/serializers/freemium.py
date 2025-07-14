from rest_framework import serializers
from ...exams.models import Exam

class ExamFreemiumSerializer(serializers.ModelSerializer):
    questions_count = serializers.IntegerField(source='questions.count', read_only=True)
    
    class Meta:
        model = Exam
        fields = ['name', 'questions_count']
        
class ExamFreemiumCreateExamAndExamTeacherSubjectSerializer(serializers.Serializer):
    subject = serializers.UUIDField()
    grade = serializers.UUIDField()
    name = serializers.CharField()