from rest_framework import serializers

from fiscallizeon.notifications.models import Notification, NotificationUser


class FeedbackOnboardingSerializer(serializers.ModelSerializer):
    rating_description = serializers.CharField(source='feedback', required=False)

    class Meta:
        model = NotificationUser
        fields = ('rating', 'rating_description', 'notification')

    def validate_notification(self, value):
        if value.category != Notification.ONBOARDING:
            raise serializers.ValidationError('Esta notificação não é válida para feedback!')
        return value
