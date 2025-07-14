from rest_framework import serializers

from fiscallizeon.subjects.models import KnowledgeArea


class KnowledgeAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeArea
        fields = '__all__'

class KnowledgeAreaSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeArea
        fields = ("id", "name", )