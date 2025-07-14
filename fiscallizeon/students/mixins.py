from .utils import MAX_STUDENTS_MESSAGE
from django.contrib import messages
from django.http.response import HttpResponseRedirect
from django.urls import reverse

class StudensLimitMixin:
    
    def dispatch(self, request, *args, **kwargs):
        user = self.request.user
        if user.is_authenticated:
            client = user.get_clients().first()
            if client.max_students_quantity:
                students_count = client.student_set.filter(user__is_active=True).count()
                if students_count >= client.max_students_quantity:
                    messages.info(self.request, MAX_STUDENTS_MESSAGE)
                    return HttpResponseRedirect(reverse('core:redirect_dashboard'))
                
        return super().dispatch(request, *args, **kwargs)