from rest_framework import serializers

from fiscallizeon.classes.models import SchoolClass

from .grade import GradeSerializer


class SchoolClassSimpleSerializer(serializers.ModelSerializer):
    grade = GradeSerializer()

    class Meta:
        model = SchoolClass
        fields = (
            'id', 'name', 'coordination', 'school_year', 'temporary_class', 'grade', 'is_itinerary'
        )
        ordering = ('name',)

    
class SchoolClassCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolClass
        fields = ('id', 'name', 'grade', 'coordination', 'class_type', 'school_year', 'turn', 'is_itinerary')
        exclude_fields = ()


class SchoolClassStudentsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchoolClass
        fields = ['id', 'name', 'coordination', 'school_year', 'students', 'is_itinerary']
        ordering = ('name', )
