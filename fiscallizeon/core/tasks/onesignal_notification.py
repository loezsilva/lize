import json
import requests
from datetime import timedelta
from django.conf import settings
from celery.schedules import crontab

from django.utils import timezone
from django.db.models.functions import Cast
from django.db.models import TextField

from fiscallizeon.celery import app
from fiscallizeon.applications.models import ApplicationStudent, Application


tomorrow = timezone.localtime(timezone.now()) + timedelta(days=1)
today = timezone.localtime(timezone.now())

headers = {
    "Accept": "text/plain",
    "Authorization": f"Basic {settings.ONESIGNAL_YOUR_REST_API_KEY}",
    "Content-Type": "application/json; charset=utf-8"
}

#Listas de exercício que inicia hoje      
@app.task
def homework_start_today():
    applications = Application.objects.filter(
        category=Application.HOMEWORK,
        duplicate_application=False,
        date=today.date()
    )
   
    for application in applications:  
        students = list(ApplicationStudent.objects.filter(
            application=application,
            student__client__allow_student_notifications=True,
        ).annotate(
            student__user__pk=Cast('student__user__pk', output_field=TextField())
        ).distinct().values_list(
            'student__user__pk', flat=True)
        )
        
        if application and students:
            payload = {
                "app_id": settings.ONESIGNAL_APP_ID,
                "include_external_user_ids": students,
                "channel_for_external_user_ids": "push",
                "contents": {
                    "en": f'Uma nova atividade inicia para você hoje: {application.exam.name.upper()}!  📚'
                },
            }
            requests.post(f"{settings.ONESIGNAL_URL}notifications", headers=headers, data=json.dumps(payload))

    pk = str(applications.first().pk) if applications else ""

    return "Homework_start_today - Executado com sucesso - " + pk
       
#Listas de exercício que vence hoje
@app.task
def homework_activity_that_expires_today():
     
    applications = Application.objects.filter(
        category=Application.HOMEWORK,
        duplicate_application=False,
        date_end=today.date()
    )
    
    for application in applications:  
        students = list(ApplicationStudent.objects.filter(
            application=application,
            student__client__allow_student_notifications=True
        ).annotate(
            student__user__pk=Cast('student__user__pk', output_field=TextField())
        ).distinct().values_list(
            'student__user__pk', flat=True)) 
        
        if students and application:
            payload = {
                "app_id": settings.ONESIGNAL_APP_ID,
                "include_external_user_ids": students,
                "channel_for_external_user_ids": "push",
                "contents": {"en": f'Prazo de entrega termina hoje: {application.exam.name.upper()} 🕦 📚'},
            }
            requests.post(f"{settings.ONESIGNAL_URL}notifications", headers=headers, data=json.dumps(payload))
    
    pk = str(applications.first().pk) if applications else ""

    return "homework_activity_that_expires_today - executada com sucesso - " + pk

#Listas de exercício que vence amanhã         
@app.task
def homework_due_tomorrow():
    
    applications = Application.objects.filter(
        category=Application.HOMEWORK,
        duplicate_application=False,
        date_end=tomorrow.date()
    )
    
    for application in applications:  
        students = list(ApplicationStudent.objects.filter(
            application=application,
            student__client__allow_student_notifications=True
        ).annotate(
            student__user__pk=Cast('student__user__pk', output_field=TextField())
        ).distinct().values_list(
            'student__user__pk', flat=True)
        ) 
        
        if students and application:
            payload = {
                "app_id": settings.ONESIGNAL_APP_ID,
                "include_external_user_ids": students,
                "channel_for_external_user_ids": "push",
                "contents": {"en": f'Prazo de entrega terminando: {application.exam.name.upper()} encerra amanhã  🕦 📚'},
            }
            requests.post(f"{settings.ONESIGNAL_URL}notifications", headers=headers, data=json.dumps(payload))

    pk = str(applications.first().pk) if applications else ""

    return "homework_due_tomorrow - Executada com sucesso  - " + pk

#Hoje sai o resultado da sua lista de exercício
@app.task        
def release_of_results_students():
    
    applications = Application.objects.filter(
        duplicate_application=False,
        student_stats_permission_date__date=today.date()
    )
    for application in applications:  
        students = list(ApplicationStudent.objects.filter(
            application=application,
            student__client__allow_student_notifications=True
        ).annotate(
            student__user__pk=Cast('student__user__pk', output_field=TextField())
        ).distinct().values_list(
            'student__user__pk', flat=True)
        ) 
        
        if students and application:
            payload = {
                "app_id": settings.ONESIGNAL_APP_ID,
                "include_external_user_ids": students,
                "channel_for_external_user_ids": "push",
                "title": "Resultado da sua lista de exercício",
                "contents": {"en": f'Hoje o resultado será liberado: {application.exam.name.upper()} 😊'},
            }
            requests.post(f"{settings.ONESIGNAL_URL}notifications", headers=headers, data=json.dumps(payload))

    pk = str(applications.first().pk) if applications else ""

    return "Release_of_results_students -  Executada com sucesso  - " + pk
            
   
# @app.on_after_finalize.connect   
# def setup_periodic_tasks(sender, **kwargs):
#     pass
    # sender.add_periodic_task(
    #     crontab(hour=11, minute=0),
    #     homework_start_today.s(),
    #     name='homework_start_today'
    # )
    # sender.add_periodic_task(
    #     crontab(hour=12, minute=0),
    #     homework_activity_that_expires_today.s(),
    #     name='homework_activity_that_expires_today'
    # )
    # sender.add_periodic_task(
    #     crontab(hour=14, minute=0),
    #     homework_due_tomorrow.s(),
    #     name='homework_due_tomorrow'
    # )
    # sender.add_periodic_task(
    #     crontab(hour=15, minute=0),
    #     release_of_results_students.s(),
    #     name='release_of_results_students'
    # )