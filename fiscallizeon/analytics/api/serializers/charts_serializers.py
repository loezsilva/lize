from rest_framework import serializers

from django.db.models import Avg

from fiscallizeon.subjects.models import KnowledgeArea, Subject
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.students.models import Student
from fiscallizeon.exams.models import Exam
from fiscallizeon.applications.models import Application
from fiscallizeon.questions.models import Question

from fiscallizeon.analytics.models import ApplicationStudentLevelQuestion, ClassSubjectApplicationLevel

class CoordinationExamSerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    class Meta:
        
        model = Exam
        fields = ['name', ]

class CoordinationStudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['pk', 'name', ]

class CoordinationQuestionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = ['pk', 'category', 'level', ]

class CoordinationApplicationsSerializer(serializers.Serializer):
    pk = serializers.UUIDField()
    exam = CoordinationExamSerializer()
    # students = CoordinationStudentSerializer(many=True)
    performance = serializers.SerializerMethodField()
    date = serializers.DateField()

    class Meta:
        # model = Application
        fields = ['pk', 'date', 'exam', 'missing_students_count', 'finish_students_count', 'performance']

    def get_performance(self, obj):
        return ClassSubjectApplicationLevel.objects.filter(
            application=obj
        ).get_performance(
            request=self.context['request']
        )

class CoordinationClassesSerializer(serializers.ModelSerializer):
    # date = serializers.DateField()
    # exam = CoordinationExamSerializer()
    students = CoordinationStudentSerializer(many=True)

    class Meta:
        model = SchoolClass
        fields = ['pk', 'name', 'students', ]


class CoordinationSubjectsSerializer(serializers.Serializer):
    pk = serializers.UUIDField()
    name = serializers.CharField()
    performance_total = serializers.DecimalField(max_digits=5, decimal_places=2)
    knowledge_area_name = serializers.CharField(source="knowledge_area.name")

    class Meta:
        fields = ['pk', 'name', 'performance_total', 'knowledge_area_name']
    
class CoordinationAreasSerializer(serializers.ModelSerializer):

    class Meta:
        model = KnowledgeArea
        fields = ['pk', 'name', ]
        



