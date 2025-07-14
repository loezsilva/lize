from django.http import HttpResponseForbidden
from django.conf import settings
from django.utils import timezone
from fiscallizeon.accounts.models import User
from fiscallizeon.applications.models import ApplicationStudent

class StudentCanViewResultsMixin:
    
    def dispatch(self, request, *args, **kwargs):
        
        user: User = self.request.user
                
        if user.is_authenticated and user.user_type == settings.STUDENT:
            
            application_student: ApplicationStudent = self.get_object()

            deny_student_stats_view = False
            
            view_exam_permission_date = application_student.application.student_stats_permission_date
            
            if view_exam_permission_date:
                today = timezone.now().astimezone()
                deny_student_stats_view = (
                    view_exam_permission_date > today
                )

            if not application_student.application.student_stats_permission_date and not application_student.application.release_result_at_end:
                return HttpResponseForbidden()

            if application_student.application.release_result_at_end:
                if not application_student.end_time and not application_student.application.is_time_finished:
                    return HttpResponseForbidden()
            elif not application_student.application.is_time_finished or deny_student_stats_view:
                return HttpResponseForbidden()
            
        return super().dispatch(request, *args, **kwargs)