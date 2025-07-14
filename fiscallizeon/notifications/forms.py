from django import forms
from .models import Notification, NotificationUser


class UserFeedbackForm(forms.ModelForm):
    class Meta:
        model = NotificationUser
        fields = ['notification', 'user', 'rating', 'feedback', 'viewed']
        
class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = "__all__"