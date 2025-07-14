from rest_framework import serializers
from fiscallizeon.integrations.models import SubjectCode


class SubjectCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubjectCode
        fields = ['id', 'subject', 'code', 'client']
        