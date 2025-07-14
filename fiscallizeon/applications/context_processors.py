from datetime import datetime, timedelta

from django.utils import timezone
from django.db.models import Q, F, ExpressionWrapper, DateTimeField
from fiscallizeon.applications.models import Application

def applications_actived(request):
    return {}
    user = request.user

    if user and not user.is_anonymous and user.user_type == 'coordination':

        start_date = ExpressionWrapper(F('date') + F('start'), output_field=DateTimeField())
        end_date = ExpressionWrapper(F('date') + F('end'), output_field=DateTimeField())

        duration_expression_start = F('start_date') - timedelta(minutes=10) + timedelta(hours=3)
        duration_wrapper_start = ExpressionWrapper(duration_expression_start, output_field=DateTimeField())

        duration_expression_end = F('end_date') + timedelta(hours=6)
        duration_wrapper_end = ExpressionWrapper(duration_expression_end, output_field=DateTimeField())

        today = timezone.localtime(timezone.now())
        now = timezone.now().astimezone()
        
        return {
            'applications_actived': Application.objects.annotate(
                start_date=start_date,
                end_date=end_date,
                limit_time_start=duration_wrapper_start,
                limit_time_end=duration_wrapper_end
            ).filter(
                Q(
                    Q(school_classes__coordination__in=user.get_coordinations()) |
                    Q(applicationstudent__student__client__in=user.get_clients_cache())
                ),
                limit_time_start__lte=now,
                limit_time_end__gte=now,
                date=today
            ).distinct()
        }

    return {}
