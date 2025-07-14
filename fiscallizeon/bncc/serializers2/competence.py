from rest_framework import serializers

from ..models import Competence


class CompetenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competence
        fields = ('id', 'code', 'text')
        ref_name = 'competence_v2'
