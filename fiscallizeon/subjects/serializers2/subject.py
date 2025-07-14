from rest_framework import serializers

from fiscallizeon.subjects.models import Subject
from fiscallizeon.classes.serializers2.grade import GradeSerializer

class SubjectSimpleSerializer(serializers.ModelSerializer):
    knowledge_area = serializers.CharField(source='knowledge_area.name')
    grades_code = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ['id', 'name', 'knowledge_area','grades_code']
        ordering = ('name', )
        ref_name = "Subjects"

    def get_grades_code(self, obj):

        # Será utilizado para filtrar as disciplinas por segmento
        grades_code = obj.knowledge_area.grades.values_list('level', flat=True) 
        
        return list(set(grades_code))