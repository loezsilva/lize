from rest_framework import serializers

from fiscallizeon.students.models import Student


class ColleagueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = (
            'name',
        )