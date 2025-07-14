from django.views.generic.edit import CreateView, UpdateView, DeleteView
from .models import Notification
from .functions import get_and_create_notifications

class NPSMixin:
    
    def dispatch(self, request, *args, **kwargs):
        
        response = super().dispatch(request, *args, **kwargs)
        
        if issubclass(type(self), CreateView):
            get_and_create_notifications(self, trigger=Notification.BEFORE_CREATE)
        elif issubclass(type(self), UpdateView):
            get_and_create_notifications(self, trigger=Notification.BEFORE_UPDATE)
        elif issubclass(type(self), DeleteView):
            get_and_create_notifications(self, trigger=Notification.BEFORE_DELETE)
            
        return response

    def get_context_data(self, **kwargs):
        
        if hasattr(self, 'get_context_data'):
            
            response = super().get_context_data(**kwargs)
            
            get_and_create_notifications(self, trigger=Notification.IN_LIST)
            
            return response