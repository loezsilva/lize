from django.utils import timezone
from rest_framework import serializers

from fiscallizeon.applications.models import Annotation, ApplicationAnnotation

class AnnotationSerializer(serializers.ModelSerializer):
    first_name = serializers.SerializerMethodField()
    function = serializers.SerializerMethodField()
    date_time = serializers.SerializerMethodField()

    class Meta:
        model = Annotation
        fields = ('application_student', 'annotation', 'first_name', 'function', 'date_time', 'suspicion_taking_advantage')

    def get_first_name(self, annotation):
        return annotation.inspector.get_user_first_name

    def get_function(self, annotation):
        return annotation.inspector.get_user_function

    def get_date_time(self, annotation):
        date_time = timezone.localtime(annotation.created_at)
        return f'{date_time.hour}:{date_time.minute}'


class ApplicationAnnotationSerializer(serializers.ModelSerializer):
    first_name = serializers.SerializerMethodField()
    function = serializers.SerializerMethodField()
    date_time = serializers.SerializerMethodField()
    suspicion_taking_advantage = serializers.CharField(source='annotation.suspicion_taking_advantage')

    class Meta:
        model = ApplicationAnnotation
        fields = ('application', 'annotation', 'first_name', 'function', 'date_time', 'suspicion_taking_advantage')

    def get_first_name(self, annotation):
        return annotation.inspector.get_user_first_name

    def get_function(self, annotation):
        return annotation.inspector.get_user_function

    def get_date_time(self, annotation):
        return f'{annotation.created_at.hour}:{annotation.created_at.minute}'