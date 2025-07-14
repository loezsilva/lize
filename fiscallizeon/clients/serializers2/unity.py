from rest_framework import serializers

from fiscallizeon.clients.models import Unity

class UnitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Unity
        fields = ['id', 'name']
        ordering = ('name', )