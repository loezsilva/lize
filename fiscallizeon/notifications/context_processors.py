from django.core.cache import cache
from django.utils import timezone
from django.db.models import Q
from fiscallizeon.notifications.models import Notification, NotificationUser

def create_notifications(notifications, user):
    
    return {
        'notifications': [],
        # 'notifications': notifications if not notifications_nps else Notification.objects.filter(pk__in=notifications).union(notifications_nps),
    }