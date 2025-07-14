from rest_framework import serializers

from ..models import Application


class ApplicationSerializer(serializers.ModelSerializer):
    classes_ids = serializers.SerializerMethodField()
    applicationstudents_ids = serializers.SerializerMethodField()
    exam_id = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    start = serializers.SerializerMethodField()
    end = serializers.SerializerMethodField()
    finish_date = serializers.SerializerMethodField()
    category_description = serializers.SerializerMethodField()
    exam_name = serializers.SerializerMethodField()


    class Meta:
        model = Application
        fields = (
            'id',
            'classes_ids',
            'applicationstudents_ids',
            'exam_id',
            'date',
            'start',
            'end',
            'finish_date',
            'category_description',
            'exam_name'
        )

    def get_exam_name(self, obj):
        return obj.exam.name
    
    def get_classes_ids(self, obj):
        return obj['classes_ids']

    def get_applicationstudents_ids(self, obj):
        return obj['applicationstudents_ids']

    def get_exam_id(self, obj):
        return obj['exam_id']

    def get_date(self, obj):
        return obj['date']

    def get_start(self, obj):
        return obj['start']

    def get_end(self, obj):
        return obj['end']

    def get_finish_date(self, obj):
        return obj['finish_date']

    def get_category_description(self, obj):
        return obj['category_description']
