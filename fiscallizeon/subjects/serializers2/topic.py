from rest_framework import serializers

from ..models import Topic


class TopicSerializer(serializers.ModelSerializer):
    grade_name = serializers.SerializerMethodField()
    stage_description = serializers.SerializerMethodField()
    creator = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = (
          'id', 'grade_name', 'subject_id', 'stage_description', 'name', 'creator',
        )
        ref_name = 'topic_v2'

    def get_grade_name(self, obj):
        return obj['grade_name']

    def get_stage_description(self, obj):
        return obj['stage_description']

    def get_creator(self, obj):
        return obj['creator']
