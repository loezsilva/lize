from rest_framework import serializers
from fiscallizeon.accounts.models import SSOTokenUser

class SSOGenerateAcessTokenSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
class SSOGenerateAcessTokenResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = SSOTokenUser
        fields = ('access_token', 'refresh_token', 'expire_in', )

class SSOLoginTokenSerializer(serializers.Serializer):
    access_token = serializers.UUIDField(required=True)