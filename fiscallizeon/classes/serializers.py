from statistics import fmean
from rest_framework import serializers
from fiscallizeon.bncc.utils import get_bncc

from fiscallizeon.classes.models import SchoolClass, Grade
from fiscallizeon.clients.serializers.coordinations import SchoolCoordinationSimpleSerializer
from fiscallizeon.exams.models import Exam
from fiscallizeon.subjects.models import Subject
# from fiscallizeon.classes.serializers import GradeSerializer


class GradeSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Grade
        fields = ['id', 'name', 'full_name']

    def get_full_name(self, obj):
        return obj.__str__()
    
class SchoolClassSimpleSerializer(serializers.ModelSerializer):
    grade = GradeSerializer()
    coordination_name = serializers.CharField(source='coordination.unity.name')
    class Meta:
        model = SchoolClass
        fields = ['id', 'name', 'grade', 'coordination_name']
        ordering = ('name', )

class SchoolClassSerializer(serializers.ModelSerializer):
    unity_name = serializers.CharField(read_only=True, source="coordination.unity.name")
    students_count = serializers.SerializerMethodField()
    students = serializers.SerializerMethodField()
    
    class Meta:
        model = SchoolClass
        fields = ['id', 'name', "date", "start", "end", "unity_name", "students_count", "students"]

    def get_students_count(self, obj):
        return obj.students.filter(user__is_active=True).count()
    
    def get_students(self, obj):
        from fiscallizeon.students.serializers.students import StudentSerializerSimple
        request = self.context.get('request', None)
        students = obj.students.filter(
            user__is_active=True
        )
        if request.GET.get('is_atypical', '').lower() == 'true':
            students = students.filter(is_atypical=True)
        elif request.GET.get('is_atypical', '').lower() == 'false':
            students = students.filter(is_atypical=False)
        return StudentSerializerSimple(students, many=True).data

class SchoolClassAndCoordinationSerializer(serializers.ModelSerializer):
    
    coordination = SchoolCoordinationSimpleSerializer(many=False)

    class Meta:
        model = SchoolClass
        fields = ['id', 'coordination']

class ClassesPerformancesSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="__str__")
    performance = serializers.SerializerMethodField()
    histogram = serializers.SerializerMethodField()
    count = serializers.IntegerField(source="students.count")

    class Meta:
        model = SchoolClass
        fields = ['id', 'name', 'performance', 'histogram', 'count']
    
    def get_performance(self, obj):
        exam = Exam.objects.get(pk=obj.exam_pk)
        if obj.subject_pk:
            subject = Subject.objects.get(pk=obj.subject_pk)
            subject_classe_performance = subject.last_performance(exam=exam, classe=obj).first()
            if subject_classe_performance:
                return float(subject_classe_performance.performance)
            return 0    
        
        if obj.bncc_pk:
            bncc = get_bncc(obj.bncc_pk)
            bncc_classe_performance= bncc.last_performance(exam=exam, classe=obj).first()
            if bncc_classe_performance:
                return float(bncc_classe_performance.performance)
            return 0 
        return 0
    
    def get_histogram(self, obj):
        exam = Exam.objects.get(pk=obj.exam_pk)
        histogram: object = {
            "data": [],
            "categories": ['0% - 20%', '21% - 40%', '41% - 60%', '61% - 80%', '81% - 100%']
        }
        
        if obj.subject_pk:
            subject = Subject.objects.get(pk=obj.subject_pk)
            subject_classe_performance = subject.last_performance(exam=exam, classe=obj).first()
            if subject_classe_performance and subject_classe_performance.histogram:
                histogram['data'] = subject_classe_performance.histogram
                
        elif obj.bncc_pk:
            bncc = get_bncc(obj.bncc_pk)
            bncc_classe_performance= bncc.last_performance(exam=exam, classe=obj).first()
            if bncc_classe_performance and bncc_classe_performance.histogram:
                histogram['data'] = bncc_classe_performance.histogram
                
        return histogram
