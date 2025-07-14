from django.urls import path

from .api.views import NotificationListAPIView, UserFeedbackUpdateAPIView, CreateEspecialNotificationAPIView, CheckNotificationAPIView

app_name = 'notifications'

urlpatterns = [
	# API
	path('api/notifications/', NotificationListAPIView.as_view(), name='api-list'),
	path('api/notifications/especiais/', CreateEspecialNotificationAPIView.as_view(), name='api-especial-notification'),
	path('api/check/notifications/', CheckNotificationAPIView.as_view(), name='api-check-notification'),
	path('api/feedback/update/<uuid:pk>/', UserFeedbackUpdateAPIView.as_view(), name='api-user-feedback-update'),
]