from rest_framework import serializers

from fiscallizeon.inspectors.models import Inspector, TeacherSubject
from fiscallizeon.subjects.models import Subject
from fiscallizeon.classes.models import SchoolClass
from django.utils import timezone
from fiscallizeon.clients.models import SchoolCoordination
from fiscallizeon.exams.models import Exam

class TeacherSubjectPkSerializer(serializers.Serializer):
    subjects = serializers.ListField(
        required=True, 
        allow_empty=False,
        child=serializers.UUIDField()
    )


class InspectorTeacherSubjectsSerializer(serializers.ModelSerializer):
    school_classes = serializers.PrimaryKeyRelatedField(
        source='classes',
        many=True, 
        queryset=SchoolClass.objects.all()
    )
    # school_year = serializers.IntegerField(default=timezone.now().year)

    class Meta:
        model = TeacherSubject
        fields = ['subject', 'active', 'school_classes'] #'school_year',


class SchoolClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolClass
        fields = ('id', 'school_year')

class InspectorSerializer(serializers.ModelSerializer):
    teacher_subjects = serializers.SerializerMethodField()
    # classes = serializers.SerializerMethodField()
    coordinations = serializers.PrimaryKeyRelatedField(queryset=SchoolCoordination.objects.all(), many=True)
    
    class Meta:
        model = Inspector
        fields = [
            'id',
            'name',
            'email',
            'coordinations',
            'teacher_subjects',
            'can_viewed',
            'can_approve', 
            'can_fail',
            'can_update_note',
            'can_suggest_correction',
            'can_annul', 
            'can_elaborate_questions',
            'can_response_wrongs', 
            'can_answer_wrongs_others_teachers',
            'can_correct_questions_other_teachers',
            'is_discipline_coordinator',
            # 'classes',
        ]
        ordering = ('name', )
        ref_name = "Teacher"

    def get_teacher_subjects(self, obj):
        if isinstance(obj, dict):
            return [] 
        queryset = obj.teachersubject_set.all().filter(active=True)
        return InspectorTeacherSubjectsSerializer(instance=queryset, many=True, read_only=True).data

    def get_classes(self, obj):
        if isinstance(obj, dict):
            return [] 
        return SchoolClassSerializer(
            instance=obj.classes_he_teaches.all(), many=True, read_only=True,
        ).data
    
class InspectorWithPermissionGroupsSerializer(InspectorSerializer):
    permission_groups = serializers.SerializerMethodField()
    is_active = serializers.SerializerMethodField()
    
    # serializers.PrimaryKeyRelatedField(queryset=CustomGroup.objects.all(), source='user.custom_groups', many=True)

    class Meta:
        model = Inspector
        fields = [
            'id',
            'name',
            'email',
            'coordinations',
            'teacher_subjects',
            'can_viewed',
            'can_approve', 
            'can_fail',
            'can_update_note',
            'can_suggest_correction',
            'can_annul', 
            'can_elaborate_questions',
            'can_response_wrongs', 
            'can_answer_wrongs_others_teachers',
            'can_correct_questions_other_teachers',
            'is_discipline_coordinator',
            # 'classes',
            'permission_groups',
            'is_active'
        ]
        ordering = ('name', )
        ref_name = "Teacher"

    def get_permission_groups(self, obj):
        if not obj.user:
            return []
        return [str(custom_group.pk) for custom_group in obj.user.custom_groups.all()]
    
    def get_is_active(self, obj):
        if not obj.user:
            return False
        return obj.user.is_active
    
class CreateExamAndExamTeacherSubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = [
            'id',
            'name', 
            'base_text_location',
            'teacher_subjects', 
            'is_english_spanish', 
            'random_alternatives', 
            'correction_by_subject', 
            'random_questions', 
            'group_by_topic'
        ]
