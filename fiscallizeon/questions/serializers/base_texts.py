from rest_framework import serializers

from fiscallizeon.questions.models import BaseText

class BaseTextSimpleSerializer(serializers.ModelSerializer):

    short_text = serializers.SerializerMethodField()

    class Meta:
        model = BaseText
        fields = ['id', 'title', 'text', 'short_text', 'created_by']

    def get_short_text(self, obj):
        return obj.get_enunciation_str()[:200]