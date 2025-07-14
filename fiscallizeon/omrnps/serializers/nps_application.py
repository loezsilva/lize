from rest_framework import serializers

from fiscallizeon.omrnps.models import NPSApplication
from fiscallizeon.omrnps.serializers.nps_axis import NPSApplicationAxisSerializer

class NPSApplicationIDSerializer(serializers.Serializer):
    nps_application_id = serializers.UUIDField()

class NPSApplicationSerializer(serializers.ModelSerializer):
    nps_axis = NPSApplicationAxisSerializer(source='npsapplicationaxis_set', many=True)
    class Meta:
        model = NPSApplication
        fields = ['id', 'date', 'name', 'nps_axis']