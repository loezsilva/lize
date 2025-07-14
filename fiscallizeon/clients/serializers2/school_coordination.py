from rest_framework import serializers

from fiscallizeon.clients.models import SchoolCoordination

class SchoolCoordinationSerializer(serializers.ModelSerializer):
    unit = serializers.UUIDField(source='unity.pk')

    class Meta:
        model = SchoolCoordination
        fields = ['id', 'name', 'unit']
        ordering = ('name', )