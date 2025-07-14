from rest_framework import serializers

from fiscallizeon.subjects.models import Theme

class ThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Theme
        fields = '__all__'

class ThemeSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Theme
        fields = ("id", "name")
    
