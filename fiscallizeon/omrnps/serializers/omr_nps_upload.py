from rest_framework import serializers

from fiscallizeon.omrnps.models import OMRNPSUpload

class OMRNPSUploadStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OMRNPSUpload
        fields = ('id', 'status')