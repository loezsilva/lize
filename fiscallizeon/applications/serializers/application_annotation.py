from rest_framework import serializers

from fiscallizeon.applications.models import ApplicationAnnotation

class ApplicationAnnotationSerializer(serializers.ModelSerializer):
    first_name = serializers.SerializerMethodField()
    function = serializers.SerializerMethodField()
    date_time = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationAnnotation
        fields = ('application', 'annotation', 'first_name', 'function', 'date_time')

    def get_first_name(self, obj):
        return obj.inspector.get_user_first_name

    def get_function(self, obj):
        return obj.inspector.get_user_function

    def get_date_time(self, obj):
        return f'{obj.created_at.hour}:{annotation.created_at.minute}'