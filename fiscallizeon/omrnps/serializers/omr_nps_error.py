from rest_framework import serializers

from fiscallizeon.omrnps.models import OMRNPSError

class OMRNPSErrorIdsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OMRNPSError
        fuelds = ['id', ]