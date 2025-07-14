from django.utils import timezone

from rest_framework import serializers

from fiscallizeon.accounts.models import User


class AccountSerializer(serializers.ModelSerializer):
    email = serializers.SerializerMethodField()
    access_token = serializers.SerializerMethodField()
    expires_in = serializers.SerializerMethodField()
    expires_unix_epoch = serializers.SerializerMethodField()
    token_type = serializers.SerializerMethodField()
    scope = serializers.SerializerMethodField()
    refresh_token = serializers.SerializerMethodField()
    client_session_timeout_minutes = serializers.SerializerMethodField()
    name = serializers.CharField(source='student.name')
    client = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id',
            'username',
            'name',
            'email',
            'nickname',
            'avatar',
            'mood',
            'background',
            'color_mode_theme',
            'has_viewed_starter_onboarding',
            'access_token',
            'expires_in',
            'expires_unix_epoch',
            'token_type',
            'scope',
            'refresh_token',
            'client_session_timeout_minutes',
            'client',
        )

    def get_email(self, obj):
        return obj.email.lower()

    def get_access_token(self, obj):
        return self.context.get('access_token', '')

    def get_expires_in(self, obj):
        return self.context.get('expires_in', 0)

    def get_expires_unix_epoch(self, obj):
        return self.context.get('expires_unix_epoch', 0)

    def get_token_type(self, obj):
        return self.context.get('token_type', '')

    def get_scope(self, obj):
        return self.context.get('scope', '')

    def get_refresh_token(self, obj):
        return self.context.get('refresh_token', '')

    def get_client_session_timeout_minutes(self, obj):
        return obj.client_session_timeout_minutes
    
    def get_client(self, obj):
        return {
            'name': obj.client.name,
            'short_name': obj.client.short_name,
            'logo': obj.client.logo.url if obj.client.logo else None,
            'small_logo': obj.client.small_logo.url if obj.client.small_logo else None,
        }


class UserStarterOnboardingSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'nickname',
            'avatar',
            'color_mode_theme',
            'background',
            'has_viewed_starter_onboarding',
        )


class UserMoodSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('mood',)
