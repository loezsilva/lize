from rest_framework import serializers

from fiscallizeon.classes.models import Grade

class GradeSerializer(serializers.ModelSerializer):
    level = serializers.CharField(source='get_level_display')
    class Meta:
        model = Grade
        fields = ('id', 'name', 'level')
        ref_name = 'grade_v2'
