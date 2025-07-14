from rest_framework import serializers
from fiscallizeon.applications.models import RandomizationVersion

class RandomizationVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RandomizationVersion
        fields = '__all__'