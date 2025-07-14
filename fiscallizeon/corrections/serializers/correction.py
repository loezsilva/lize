from rest_framework import serializers
from fiscallizeon.corrections.models import CorrectionTextualAnswer, CorrectionFileAnswer, CorrectionCriterion, CorrectionDeviation

class CorrectionCriterionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CorrectionCriterion
        fields = ['id', 'name', 'maximum_score', 'color', 'short_name', 'description']
class TextCorrectionSerializer(serializers.ModelSerializer):
    criterions = CorrectionCriterionSerializer(source='correctioncriterion_set', many=True)
    class Meta:
        model = CorrectionCriterion
        fields = ['id', 'name', 'criterions']

class DeviationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CorrectionDeviation
        fields = ['id', 'short_name', 'description', 'score']
    
class CorrectionTextualAnswerSerializer(serializers.ModelSerializer):

    class Meta:
        model = CorrectionTextualAnswer
        fields = '__all__'

class CorrectionFileAnswerSerializer(serializers.ModelSerializer):

    class Meta:
        model = CorrectionFileAnswer
        fields = '__all__'

class CorrectionTextualAnswerOrderSerializer(serializers.ModelSerializer):
    order = serializers.IntegerField(source='correction_criterion.order')
    class Meta:
        model = CorrectionTextualAnswer
        fields = ('id', 'textual_answer', 'correction_criterion', 'order', 'point')

class CorrectionFileAnsweOrderSerializer(serializers.ModelSerializer):
    order = serializers.IntegerField(source='correction_criterion.order')
    class Meta:
        model = CorrectionFileAnswer
        fields = ('id', 'file_answer', 'correction_criterion', 'order', 'point')
