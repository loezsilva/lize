from rest_framework import serializers

from fiscallizeon.questions.models import QuestionOption


class QuestionOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = '__all__'