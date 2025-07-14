from django.utils import timezone

from celery.schedules import crontab
from datetime import timedelta
from django.db.models import Q

from fiscallizeon.celery import app
from fiscallizeon.applications.models import ApplicationStudent, Application, HashAccess

today = timezone.localtime(timezone.now())

@app.task
def notify_parent_when_result_open():
    
    applications = Application.objects.filter(
        student_stats_permission_date__date=today.date(),
        duplicate_application=False,
    )
    for application in applications:
        
        students = ApplicationStudent.objects.filter(
            Q(application=application),
            Q(student__responsible_email__isnull=False),
            Q(
                Q(start_time__isnull=False) |
                Q(is_omr=True)
            )
        ).distinct()
        
        for student in students:
            HashAccess.objects.create(
                application_student=student,
                validity=today+timedelta(days=15)
            )

    pk = str(applications.first().pk) if applications else ""


    return "notify_parent_when_result_open - " + pk
                   
            
# @app.on_after_finalize.connect   
# def setup_periodic_tasks(sender, **kwargs):
#     sender.add_periodic_task(
#         crontab(hour=15, minute=0),
#         notify_parent_when_result_open.s(),
#         name='notify_parent_when_result_open'
#     )