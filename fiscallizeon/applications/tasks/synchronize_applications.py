from celery.schedules import crontab
from datetime import datetime, timedelta
from django.core import management

from fiscallizeon.celery import app
from fiscallizeon.applications.management.commands import finish_application_students, synchronize_applications


@app.task
def finish_application_students():
    try:
        management.call_command('finish_application_students')

        
    except Exception as e:
        print(e)

@app.task
def synchronize_applications():
    try:
        yesterday_date = (datetime.now() - timedelta(days=1)).date().strftime('%d-%m-%Y')

        management.call_command('synchronize_applications', yesterday_date, yesterday_date, True)
    except Exception as e:
        print(e)

# @app.on_after_finalize.connect
# def setup_periodic_tasks(sender, **kwargs):    
#     sender.add_periodic_task(
#         crontab(hour=3, minute=10),
#         finish_application_students.s(),
#         name='finish_application_students'
#     )

#     sender.add_periodic_task(
#         crontab(hour=3, minute=20),
#         synchronize_applications.s(),
#         name='synchronize_applications'
#     )