from rest_framework import serializers
from fiscallizeon.integrations.models import SuperProfIntegration

class SuperProfIntegrationSerializer(serializers.ModelSerializer):
    
    class Meta:
        fields = '__all__'
        model = SuperProfIntegration
        
class SuperProfIntegrationSimpleSerializer(serializers.ModelSerializer):
    
    class Meta:
        fields = ['id', 'login', 'authorization_code', 'authorization_expires_at', 'access_token', 'access_token_expires_at', 'sso_token', 'sso_token_expires_at']
        model = SuperProfIntegration