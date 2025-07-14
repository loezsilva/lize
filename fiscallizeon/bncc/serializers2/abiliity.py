from rest_framework import serializers

from ..models import Abiliity


class AbiliitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Abiliity
        fields = ('id', 'code', 'text')
