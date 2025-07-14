from django.db import models
from django.utils import timezone
from django.apps import apps
from django.db.models import Q, F, Subquery, OuterRef, ExpressionWrapper, DateField, BooleanField, Value
from django.db.models.functions import Coalesce
from django.conf import settings
from datetime import timedelta

class NotificationQuerySet(models.QuerySet):
    def __init__(self, *args, **kwargs):
        self.now = timezone.localtime(timezone.now())
        return super(NotificationQuerySet, self).__init__(*args, **kwargs)

    def get_active(self, user):
        Notification = apps.get_model('notifications', 'Notification')

        active_notifications = Notification.objects.none()

        if user.is_freemium:
            active_notifications = Notification.objects.filter(
                Q(start_date__lte=self.now),
                Q(end_date__gte=self.now),
                Q(
                    Q(segments__contains=[settings.TEACHER])
                ),
                Q(users__isnull=True),
            ).order_by('-start_date')
            
        
        else:
            if client := user.client:
                active_notifications = Notification.objects.filter(
                    Q(start_date__lte=self.now),
                    Q(end_date__gte=self.now),
                    Q(
                        Q(segments__contains=[user.user_type])
                    ),
                    Q(clients=client),
                    Q(users__isnull=True)
                ).order_by('-start_date')

                if user.user_type != settings.PARTNER:
                    active_notifications = active_notifications.filter(
                        Q(
                            Q(high_school=user.has_high_school_coordinations) |
                            Q(elementary_school=user.has_elementary_school_coordinations)
                        )
                    )

        user_notifications = Notification.objects.filter(
            Q(start_date__lte=self.now),
            Q(end_date__gte=self.now),
            Q(users=user),
        ).order_by('-start_date')

        return active_notifications.distinct() | user_notifications.distinct()
    
    def get_annotations(self, user):
        Notification = apps.get_model('notifications', 'Notification')
        NotificationUser = apps.get_model('notifications', 'NotificationUser')
        
        return self.annotate(
            is_nps=models.Case(
                models.When(Q(
                    Q(repeat_days__gt=0, category=Notification.SEARCH)
                ), then=models.Value(True)), default=models.Value(False)
            ),
            viewed=Coalesce(
                Subquery(
                    NotificationUser.objects.filter(notification=OuterRef('pk'), user=user).order_by('-created_at').values('viewed')[:1], output_field=BooleanField(),
                ),
                Value(False),
                output_field=BooleanField()
            ),
            last_nps_date=Subquery(
                NotificationUser.objects.filter(notification=OuterRef('pk'), user=user).order_by('-created_at').values('next_nps_date')[:1]
            ),
            next_nps_date=ExpressionWrapper(F('last_nps_date') + timedelta(days=1) * F('repeat_days'), output_field=DateField()),
            last_feedback=Subquery(
                NotificationUser.objects.filter(notification=OuterRef('pk'), user=user).order_by('-created_at').values('feedback')[:1]
            ),
            last_rating=Subquery(
                NotificationUser.objects.filter(notification=OuterRef('pk'), user=user).order_by('-created_at').values('rating')[:1]
            ),
        )


NotificationManager = models.Manager.from_queryset(NotificationQuerySet)