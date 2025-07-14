from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, UpdateAPIView
from django.contrib.auth.mixins import LoginRequiredMixin
from fiscallizeon.core.api.csrf_exempt_session import CsrfExemptSessionAuthentication
from ..models import Notification, NotificationUser
from .serializers import NotificationUserSerializer
from django.utils import timezone
from django.db.models import Q
from fiscallizeon.core.utils import CamelCaseAPIMixin
from django.db.models.functions import Length
from rest_framework import status

from fiscallizeon.notifications.models import Notification
from fiscallizeon.notifications.functions import get_and_create_notifications

class NotificationListAPIView(LoginRequiredMixin, CamelCaseAPIMixin, ListAPIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    serializer_class = NotificationUserSerializer
    model = NotificationUser
    queryset = NotificationUser.objects.all()
    
    def create_notifications_without_triggers(self, notifications):        
        user = self.request.user
        for notification in notifications.filter(trigger__isnull=True, especial_trigger__isnull=True):
            notification.create_notificationuser(user)
    
    def active_notifications(self):
        
        now = timezone.localtime(timezone.now())
        user = self.request.user
        
        if user.is_anonymous:
            return NotificationUser.objects.none()
        
        url_path = self.request.GET.get('url_path')
        
        notifications_query = Notification.objects.get_active(user).get_annotations(user).annotate(urls_length=Length('urls')).filter(
            Q(
                Q(urls_length=0) | Q(urls__contains=url_path)
            ) if url_path else Q()
        )
        
        not_viewed_notifications = notifications_query.exclude(notificationuser__user=user)
        
        self.create_notifications_without_triggers(not_viewed_notifications)
        
        notifications = NotificationUser.objects.filter(
            Q(
                notification__in=notifications_query,
                user=user,
                next_nps_date__lte=now,
            ),
            ~Q(NotificationUser.filter_is_nps()) |
            Q(
                Q(viewed=False)
            ),
            ~Q(
                Q(viewed=True) & Q(notification__display_until_end_date=False)
            ),
        )

        return notifications
    
    def get_queryset(self):
        
        queryset = super().get_queryset().filter(pk__in=self.active_notifications()).order_by('-created_at') 
        
        return queryset.distinct()
    
    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        active_notifications = self.active_notifications()

        visible_notifications_count = active_notifications.filter(
            Q(viewed=False) | 
            Q(notification__display_until_end_date=True) |
            (Q(notification__category__in=[Notification.FEATURE, Notification.ANNOUNCEMENT]) & Q(viewed=False))  # Conta apenas se for categoria 1 ou 2 e não tiver sido vista
        ).count()
        
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            'visible_notifications_count': visible_notifications_count,
            'notifications': serializer.data
        }, status=status.HTTP_200_OK)

class UserFeedbackUpdateAPIView(LoginRequiredMixin, CamelCaseAPIMixin, UpdateAPIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    serializer_class = NotificationUserSerializer
    queryset = NotificationUser.objects.all()
    model = NotificationUser
    
    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset.filter(user=user).order_by('-next_nps_date')
        
        return queryset

class CheckNotificationAPIView(LoginRequiredMixin, CamelCaseAPIMixin, APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    
    def post(self, request, pk=None):
        
        view_type = request.data.get('view_type')
        app_label = request.data.get('app_label')
        
        if view_type and app_label:
            if view_type == 'create':
                get_and_create_notifications(view=self, trigger=Notification.AFTER_CREATE, nps_app_label=app_label)
            if view_type == 'update':
                get_and_create_notifications(view=self, trigger=Notification.AFTER_UPDATE, nps_app_label=app_label)
            if view_type == 'delete':
                get_and_create_notifications(view=self, trigger=Notification.AFTER_DELETE, nps_app_label=app_label)
        
        return Response()
class CreateEspecialNotificationAPIView(LoginRequiredMixin, CamelCaseAPIMixin, APIView):
    authentication_classes = [CsrfExemptSessionAuthentication]
    
    def post(self, request, pk=None):
        
        now = timezone.localtime(timezone.now())
        
        where = request.data.get('where')
        
        user = self.request.user
        
        notifications = Notification.objects.get_active(user).get_annotations(user).filter(
            Q(
                Q(viewed=False) |
                Q(next_nps_date__lte=now.date())
            ),
            Q(especial_trigger__isnull=False)
        )
        
        if where:
            
            especial_trigger = None
            
            if where == 'after_diagramation': 
                especial_trigger=Notification.AFTER_DIAGRAMATION
                
            elif where == 'after_send_note': 
                especial_trigger=Notification.AFTER_SEND_NOTE_FOR_ACTIVE
                
            elif where == 'after_view_exam_results': 
                especial_trigger=Notification.AFTER_VIEW_EXAM_RESULTS
                
            elif where == 'after_view_student_application_results': 
                especial_trigger=Notification.AFTER_VIEW_STUDENT_APPLICATION_RESULTS
                
            elif where == 'after_student_review_questions': 
                especial_trigger=Notification.AFTER_STUDENT_REVIEW_QUESTIONS
                
            elif where == 'in_view_exam_results': 
                especial_trigger=Notification.IN_VIEW_EXAM_RESULTS
            
            if especial_trigger:
                notifications = notifications.filter(especial_trigger=especial_trigger)
                
                for notification in notifications:
                    notification.create_notificationuser(user=user)
        
        return Response()