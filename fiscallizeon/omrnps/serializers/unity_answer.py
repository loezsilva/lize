from rest_framework import serializers

from fiscallizeon.omrnps.models import UnityAnswer

class UnityAnswerSerializer(serializers.ModelSerializer):

    class Meta:
        model = UnityAnswer
        fields = ['id', 'grade', 'omr_nps_page', 'created_by', ]