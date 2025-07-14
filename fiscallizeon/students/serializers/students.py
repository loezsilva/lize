from rest_framework import serializers

from django.utils import timezone

from fiscallizeon.students.models import Student
class StudentSerializer(serializers.ModelSerializer):
    classes = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ['id', 'name', 'classes', 'enrollment_number']
        ordering = ('name', )

    def get_classes(self, student):
        self.context.get('without_classes', False)
        if self.context.get('without_classes'):
            return []
        from fiscallizeon.classes.serializers import SchoolClassSimpleSerializer
        return SchoolClassSimpleSerializer(student.classes.all(), many=True).data


class StudentSerializerSimple(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = ['id', 'name']
        

class StudentAndClassesSerializer(serializers.ModelSerializer):
    classes = serializers.SerializerMethodField()

    class Meta:
        model = Student
        fields = ['id', 'classes']

    def get_classes(self, student):
        from fiscallizeon.classes.serializers import SchoolClassAndCoordinationSerializer
        
        current_year = timezone.now().year
        
        return SchoolClassAndCoordinationSerializer(
            student.classes.filter(temporary_class=False, school_year=current_year).order_by('-created_at')[:1],
            many=True
        ).data

        