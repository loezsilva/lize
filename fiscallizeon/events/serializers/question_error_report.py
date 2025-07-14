from rest_framework import serializers

from fiscallizeon.events.models import QuestionErrorReport
from fiscallizeon.questions.serializers.questions import QuestionSerializerSimple

class QuestionErrorReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionErrorReport
        fields = ['pk', 'application', 'content', 'question', 'sender', 'created_at']
        read_only_fields = ('created_at', 'sender')

    def to_representation(self, instance):
        response = super().to_representation(instance)
        response['question'] = QuestionSerializerSimple(instance.question).data
        return response