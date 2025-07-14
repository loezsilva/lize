from rest_framework import serializers
from fiscallizeon.clients.models import SchoolCoordination

class SchoolCoordinationSimpleSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = SchoolCoordination
        fields = ['id']