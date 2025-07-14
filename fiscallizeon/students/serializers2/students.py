from rest_framework import serializers

from django.utils import timezone

from fiscallizeon.students.models import Student
from fiscallizeon.classes.models import SchoolClass
from fiscallizeon.classes.serializers2.school_class import SchoolClassSimpleSerializer


class StudentSerializer(serializers.ModelSerializer):
    classes = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)
    username = serializers.SerializerMethodField()
    
    class Meta:
        model = Student
        fields = [
            'id', 'name', 'enrollment_number', 'client', 'classes', 
            'email', 'responsible_email', 'is_active', 'username'
        ]
        ordering = ('name', )
        extra_kwargs = {'client': {'write_only': True}}
        ref_name = "Students"

    def get_classes(self, student):
        return SchoolClassSimpleSerializer(
            student.classes.filter(school_year=timezone.now().year),
            many=True
        ).data
        
    def get_username(self, student):
        return student.user.username if student.user else None

    def create(self, validated_data):
        print(validated_data)
        return Student.objects.create(**validated_data)
    
class StudentCreateUpdateSerializer(serializers.ModelSerializer):
    classes = serializers.SerializerMethodField()
    username = serializers.CharField(default="")
    password = serializers.CharField(default="")
    is_active = serializers.BooleanField(source='user.is_active', read_only=True)

    class Meta:
        model = Student
        fields = [
            'name', 'enrollment_number', 'classes', 
            'email', 'responsible_email', 'is_active', 'username', 'password'
        ]
        ordering = ('name', )
        extra_kwargs = {'client': {'write_only': True}}

    def get_classes(self, student):
        return SchoolClassSimpleSerializer(
            student.classes.filter(school_year=timezone.now().year),
            many=True
        ).data

    def get_username(self, student):
        return student.user.username if student.user else None

        
class StudentSchoolClassesSerializer(serializers.Serializer):
    school_classes = serializers.PrimaryKeyRelatedField(
        many=True, 
        queryset=SchoolClass.objects.all()
    )