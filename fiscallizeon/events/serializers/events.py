from rest_framework import serializers

from fiscallizeon.events.models import Event

class CreateEventSerializer(serializers.ModelSerializer):
    inspector_first_name = serializers.SerializerMethodField()
    student_pk = serializers.SerializerMethodField()


    class Meta:
        model = Event
        fields = ['pk', 'event_type', 'student_application', 'inspector_first_name', 'start', 'end', 'get_response_display', 'get_event_type_display', 'response_datetime', 'created_at', 'student_pk']
        read_only_fields = ('start', 'end', 'get_response_display', 'get_event_type_display', 'response_datetime', 'created_at', 'student_pk')

    def get_inspector_first_name(self, obj):
        return obj.inspector.get_user_first_name if obj.inspector else ""

    def get_student_pk(self, obj):
        return obj.student_application.pk


class FinishEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['pk',]
        read_only_fields = ('pk', )


class UpdateEventSerializer(serializers.ModelSerializer):
    response = serializers.IntegerField(required=True)
    inspector_first_name = serializers.SerializerMethodField()
    student_pk = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = ['pk', 'event_type', 'inspector_first_name', 'start', 'end', 'get_response_display', 'get_event_type_display', 'response_datetime', 'created_at', 'response', 'student_pk']
        read_only_fields = ('start', 'end', 'get_response_display', 'get_event_type_display', 'response_datetime', 'created_at', 'student_pk')
        write_only_fields = ('response', )

    def get_inspector_first_name(self, obj):
        return obj.inspector.get_user_first_name if obj.inspector else ""

    def get_student_pk(self, obj):
        return obj.student_application.pk

    
