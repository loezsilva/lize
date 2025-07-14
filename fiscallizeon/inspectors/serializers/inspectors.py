from django.utils import timezone
from rest_framework import serializers
from fiscallizeon.inspectors.models import Inspector, TeacherSubject
from fiscallizeon.subjects.serializers.subjects import SubjectSimpleSerializer

class InspectorSimpleSerializer(serializers.ModelSerializer):
    user_first_name = serializers.CharField(source="name")
    
    class Meta:
        model = Inspector
        fields = ['id', 'name', 'user_first_name',  'is_inspector_ia']

class TeacherSubjectVerySimpleSerializer(serializers.ModelSerializer):
    teacher = InspectorSimpleSerializer(many=False, read_only=True)
    subject = SubjectSimpleSerializer(many=False, read_only=True)
    
    class Meta:
        model = TeacherSubject
        fields = ['id', 'teacher', 'subject']

class TeacherSubjectSerializer(serializers.ModelSerializer):
    teacher = InspectorSimpleSerializer(many=False, read_only=True)
    subject = SubjectSimpleSerializer(many=False, read_only=True)
    classes = serializers.SerializerMethodField()
    grades = serializers.SerializerMethodField()
    show_all = serializers.BooleanField(default=False)
    protected = serializers.SerializerMethodField()
    
    class Meta:
        model = TeacherSubject
        fields = ['id', 'teacher', 'subject', 'classes', 'grades', 'show_all', 'protected']
        
    def get_grades(self, obj):
        return [grade.id for grade in obj.get_grades()] if obj.get_grades() else []
    
    def get_classes(self, obj):
        return [classe.id for classe in obj.classes.filter(school_year=timezone.now().year)] if obj.classes.exists() else []

    def get_protected(self, obj):
        return True if obj.examteachersubject_set.all().exists() else False

class TeacherSubjectSimpleSerializer(serializers.ModelSerializer):
    teacher = InspectorSimpleSerializer(many=False, read_only=True)
    subject = SubjectSimpleSerializer(many=False, read_only=True)
    grades = serializers.SerializerMethodField()

    
    class Meta:
        model = TeacherSubject
        fields = ['id', 'teacher', 'subject', 'grades']
    
    def get_grades(self, obj):
        return [grade.id for grade in obj.get_grades()] if obj.get_grades() else []
    
class InspectorSerializer(serializers.ModelSerializer):
    subjects = serializers.SerializerMethodField()

    class Meta:
        model = Inspector
        fields = '__all__'
        
    def get_subjects(self, obj):
        teacher_subjects = TeacherSubject.objects.using('default').filter(
            teacher=obj,
            school_year=timezone.now().year,
            active=True
        ).distinct('subject')
        return TeacherSubjectSerializer(instance=teacher_subjects, many=True, read_only=True).data

class InspectorsCreateUpdateSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Inspector
        exclude = ['created_at', 'updated_at', ]


class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inspector
        fields = ('id', 'name')
        
class TeacherSerializerChangeExperience(serializers.ModelSerializer):
    class Meta:
        model = Inspector
        fields = ['has_new_teacher_experience']

class InspectorTutorialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inspector
        fields = ['show_questions_bank_tutorial']
