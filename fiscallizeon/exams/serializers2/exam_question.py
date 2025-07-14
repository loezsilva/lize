from rest_framework import serializers

from ..models import ExamQuestion


class ExamQuestionSerializer(serializers.ModelSerializer):
    request_id = serializers.SerializerMethodField()
    status_description = serializers.SerializerMethodField()

    class Meta:
        model = ExamQuestion
        fields = (
            'id',
            'question_id',
            'exam_id',
            'request_id',
            'order',
            'weight',
            'status_description',
        )
        ref_name = 'exam_question_v2'

    def get_request_id(self, obj):
        return obj['request_id']

    def get_status_description(self, obj):
        return obj['status_description']
