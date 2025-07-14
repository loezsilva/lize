from rest_framework import serializers

from fiscallizeon.omrnps.models import NPSAxis, NPSApplicationAxis

class NPSAxisSerializer(serializers.ModelSerializer):
    class Meta:
        model = NPSAxis
        exclude = ['created_at', 'updated_at']

class NPSApplicationAxisSerializer(serializers.ModelSerializer):
    class Meta:
        model = NPSApplicationAxis
        exclude = ['created_at', 'updated_at', ]