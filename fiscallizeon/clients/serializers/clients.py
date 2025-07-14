from rest_framework import serializers
from fiscallizeon.clients.models import ClientTeacherObligationConfiguration
from ..models import Client


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ('id', 'name',)
        
class ClientTeacherObligationConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientTeacherObligationConfiguration
        fields = ('id', 'level', 'template', 'topics', 'abilities', 'competences', 'difficult', 'pedagogical_data', 'commented_response', 'apply_on_homework')
    
