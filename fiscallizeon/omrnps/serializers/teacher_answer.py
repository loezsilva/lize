from rest_framework import serializers

from fiscallizeon.omrnps.models import TeacherAnswer

class TeacherAnswerSerializer(serializers.ModelSerializer):
    nps_axis = serializers.UUIDField(source='nps_application_axis.nps_axis.id', read_only=True)
    nps_axis_index = serializers.IntegerField(source='nps_application_axis.order', read_only=True)
    class Meta:
        model = TeacherAnswer
        exclude = ['created_at', 'updated_at', ]
        write_only_fields = ['omr_nps_page', ]