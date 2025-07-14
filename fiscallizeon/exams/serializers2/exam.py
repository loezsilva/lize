from rest_framework import serializers

from ..models import Exam


class ExamSerializer(serializers.ModelSerializer):
    # status_description = serializers.SerializerMethodField()
    # creator = serializers.SerializerMethodField()
    # total_weight = serializers.SerializerMethodField()
    id_erp = serializers.SerializerMethodField()
    stage_id_erp = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = (
            'id',
            'name',
            # 'status_description',
            # 'random_alternatives',
            # 'random_questions',
            # 'is_english_spanish',
            # 'category',
            # 'correction_by_subject',
            'elaboration_deadline',
            # 'creator',
            # 'release_elaboration_teacher',
            # 'show_ranking',
            # 'total_weight',
            'id_erp',
            'stage_id_erp',
            'created_at',
            'teaching_stage',
            'education_system'
        )

    # def get_status_description(self, obj):
    #     return obj['status_description']

    # def get_creator(self, obj):
    #     return obj['creator']

    # def get_total_weight(self, obj):
    #     return obj.total_weight

    def get_id_erp(self, obj):
        return obj['id_erp']

    def get_stage_id_erp(self, obj):
        return obj['stage_id_erp']
