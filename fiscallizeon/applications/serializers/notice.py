from rest_framework import serializers
from fiscallizeon.applications.models import ApplicationNotice


class ApplicationNoticeSerializer(serializers.ModelSerializer):
    first_name = serializers.SerializerMethodField()
    function = serializers.SerializerMethodField()
    date_time = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationNotice
        fields = ('application', 'notice', 'first_name', 'function', 'date_time')

    def get_first_name(self, notice):
        return notice.inspector.get_user_first_name

    def get_function(self, notice):
        return notice.inspector.get_user_function

    def get_date_time(self, notice):
        return f'{notice.created_at.hour}:{notice.created_at.minute}'