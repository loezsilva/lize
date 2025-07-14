from rest_framework import serializers

from fiscallizeon.events.models import ApplicationMessage

class ApplicationMessageSerializer(serializers.ModelSerializer):

    class Meta:
        model = ApplicationMessage
        fields = ['pk', 'application', 'content', 'created_at']
        read_only_fields = ('created_at', )