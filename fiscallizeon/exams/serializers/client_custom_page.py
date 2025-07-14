from rest_framework import serializers
from fiscallizeon.exams.models import ClientCustomPage

class ClientCustomPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientCustomPage
        fields = ['name', 'location', 'content']