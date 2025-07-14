from .models import Notification
from django.db.models import Q
from django.utils import timezone

def get_and_create_notifications(view, trigger, nps_app_label = None):
    
    now = timezone.localtime(timezone.now())
    
    notifications = []

    model = nps_app_label if nps_app_label else None
    
    if not model:
        
        if hasattr(view, 'nps_app_label'):
            model = view.nps_app_label
        
            
        elif hasattr(view, 'model') and view.model:
            model = view.model._meta.label
        
        elif hasattr(view, 'queryset'):
            model = view.queryset.model._meta.label
    
    user = view.request.user
    
    if model:
        
        notifications = Notification.objects.get_active(user).get_annotations(user).filter(
            Q(
                trigger=trigger,
                model=model,
            ),
            Q(
                Q(viewed=False) | Q(next_nps_date__lte=now.date())
            )
        )
        
        for notification in notifications:
            notification.create_notificationuser(user)