from rest_framework import serializers

from ..models import BaseText


class BaseTextSerializer(serializers.ModelSerializer):
    creator = serializers.SerializerMethodField()

    class Meta:
        model = BaseText
        fields = ('id', 'title', 'text', 'creator')
        ref_name = 'base_text_v2'

    def get_creator(self, obj):
        return obj.created_by.name
