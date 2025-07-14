from rest_framework import serializers
from ..models import Notification, NotificationUser

class NotificationSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display')
    is_nps = serializers.SerializerMethodField()
    viewed = serializers.SerializerMethodField()
    last_feedback = serializers.SerializerMethodField()
    last_rating = serializers.SerializerMethodField()
        
    class Meta:
        model = Notification
        fields = ["id", "category", "content", "answer_is_required", "delay", "description", "modal_height", "modal_width", "persist", "show_form", "show_modal", "nps_type", "show_rating", "title", "category_display", "is_nps", "viewed", "last_feedback", "last_rating"]
    
    def get_is_nps(self, obj):
        return obj.is_nps
    
    def get_viewed(self, obj):
        return obj.viewed
    
    def get_last_feedback(self, obj):
        return obj.last_feedback
    
    def get_last_rating(self, obj):
        return obj.last_rating
    
class NotificationSimpleSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display')
    
    class Meta:
        model = Notification
        fields = ["id", "category", "content", "answer_is_required", "delay", "description", "modal_height", "modal_width", "persist", "show_form", "show_modal", "nps_type", "show_rating", "title", "category_display", "repeat_days", "end_date",  "display_until_end_date"]
    
class NotificationUserSerializer(serializers.ModelSerializer):
    notification = NotificationSimpleSerializer(read_only=True)
    is_nps = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    urls = serializers.JSONField(required=False)
    
    class Meta:
        model = NotificationUser
        fields = ["id", "notification", "rating", "viewed", "feedback", "feedback_sent", "solved", "next_nps_date", "is_nps", "urls", "type"]
    
    def get_is_nps(self, obj):
        return obj.notification.get_is_nps
    
    def get_type(self, obj):
        return obj.notification.type