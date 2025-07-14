from rest_framework import serializers

from fiscallizeon.events.models import TextMessage

class CreateTextMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = TextMessage
        fields = ['pk', 'application_student', 'content']
