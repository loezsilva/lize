from rest_framework import serializers
from fiscallizeon.accounts.models import User
    
class UserSimpleSerializer(serializers.ModelSerializer):
    urls = serializers.JSONField()
    class Meta:
        model = User
        fields = ('name', 'urls')