from rest_framework import serializers

from fiscallizeon.subjects.models import MainTopic

class MainTopicSerializer(serializers.ModelSerializer):
    class Meta:
        model = MainTopic
        fields = '__all__'


class MainTopicSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MainTopic
        fields = ['id', 'name', 'theme']
    
    def validate(self, data):
        theme = data.get('theme')
        if not theme:
            raise serializers.ValidationError("Necessário adicioaar o tema.")
        return data
