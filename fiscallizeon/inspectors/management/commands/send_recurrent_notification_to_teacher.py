from typing import Any
from django.utils import timezone
from django.db.models import OuterRef, Subquery, Exists, F, Q, SmallIntegerField, Value, Count, Func
from django.db.models.functions import Coalesce
from django.core.management.base import BaseCommand
from fiscallizeon.exams.models import Exam, ExamTeacherSubject, ExamQuestion

from fiscallizeon.clients.models import ConfigNotification, Client
from fiscallizeon.accounts.models import User
from fiscallizeon.inspectors.models import Inspector
from datetime import timedelta
from django.template.loader import get_template
from fiscallizeon.core.threadings.sendemail import EmailThread
from django.conf import settings


class Command(BaseCommand):
    help = 'Command para enviar email periodicamente para professores com cadernos não entregues'

    @property
    def get_examquestion_availables_subquery(self):
        return Coalesce(
            Subquery(
                ExamQuestion.objects.filter(
                    exam_teacher_subject=OuterRef('pk'),
                ).availables(
                    exclude_use_later=False, 
                    exclude_correction_pending=True
                ).order_by().annotate(
                    count=Func(F('id'), function='Count')
                ).distinct().values('count')[:1],
                output_field=SmallIntegerField(),
            ), Value(0)
        )

    def send_notification_to_teachers(self, config, deadline, after_expiration):
        
        now = timezone.localtime(timezone.now())
        
        today = now.today()
        
        if deadline:
            
            client = config.client
            
            teachers = Inspector.objects.filter(
                coordinations__unity__client=client,
                user__is_active=True,
            ).exclude(
                is_abstract=True
            ).distinct()
            
            exams = Exam.objects.filter(
                Q(
                    is_abstract=False,
                    status=Exam.ELABORATING,
                    elaboration_deadline=deadline,
                ), 
                Q(
                    Q(release_elaboration_teacher__isnull=True) |
                    Q(release_elaboration_teacher__lte=today)
                )
            )
            
            teachers = teachers.filter(teachersubject__in=exams.values_list('teacher_subjects', flat=True)).distinct()
            
            for teacher in teachers:
                
                exams_filtreds = exams.filter(teacher_subjects__teacher=teacher).annotate(
                    await_question=Exists(
                        ExamTeacherSubject.objects.filter(
                            teacher_subject__teacher=teacher,
                            exam__pk=OuterRef('pk'),
                        ).annotate(
                            examquestions_available_count=self.get_examquestion_availables_subquery,
                        ).filter(examquestions_available_count__lt=F('quantity'))
                    )
                ).filter(await_question=True).distinct()

                exams_count = exams_filtreds.count()
                
                if exams_count:
                    
                    diff_days = (deadline - today.today().date()).days
                    
                    subject = f"Você só tem mais um dia para inserir questões em {exams_count} instrumento avaliativo" if diff_days == 1 else f"Você só tem mais {diff_days} dias para inserir questões em { 'um instrumento avaliativo' if exams_count == 1 else str(exams_count) +' instrumentos avaliativos'}"
                    
                    if after_expiration:
                        subject = 'Um instrumento avaliativo passou do prazo para inserir questões' if exams_count == 1 else f'{exams_count} instrumentos avaliativos passou do prazo para inserir questões'
                    
                    template = get_template('mail_template/send_to_teachers_elaboration_deadline.html')
                    
                    html = template.render({ 
                        "name": teacher.name, 
                        "exams_count": exams_count, 
                        "deadline": deadline, 
                        "after_expiration": after_expiration,
                        "BASE_URL": settings.BASE_URL,
                        "diff_days": diff_days,
                    })
                    
                    subject = subject
                    
                    to = [teacher.email]
                    
                    EmailThread(subject, html, to).start()
                    
                    return
            
    def send_notification_to_coordination(self, config, deadline, after_expiration):
        
        today = timezone.localtime(timezone.now()).today()
        
        
        if deadline:
            
            diff_days = (deadline - today.date()).days
            
            client = config.client
            
            coordinators_users = User.objects.filter(
                coordination_member__coordination__unity__client=client,
                coordination_member__is_coordinator=True,
                is_active=True,
            ).distinct()
            
            exams = Exam.objects.filter(
                Q(
                    is_abstract=False,
                    status=Exam.ELABORATING,
                    elaboration_deadline=deadline,
                    coordinations__in=coordinators_users.values('coordination_member__coordination'), 
                ), 
                Q(
                    Q(release_elaboration_teacher__isnull=True) |
                    Q(release_elaboration_teacher__lte=today)
                )
            ).annotate(
                await_question=Exists(
                    ExamTeacherSubject.objects.filter(
                        pk__in=OuterRef('examteachersubject'),
                    ).annotate(
                        examquestions_available_count=self.get_examquestion_availables_subquery
                    ).filter(examquestions_available_count__lt=F('quantity'))
                )
            ).filter(await_question=True)
            
            for user in coordinators_users:
                
                coordination_exams = exams.filter(coordinations__in=user.get_coordinations_cache()).distinct()
                
                coordination_exams_count = coordination_exams.count()
                
                if coordination_exams_count:
                    
                        
                    if after_expiration:
                        subject = 'Existem cadernos que passaram do prazo para inserir questões'
                    else:
                        if diff_days > 1:
                            subject = f"Faltam {diff_days} dias para o prazo de {coordination_exams_count} caderno(s) encerrar"
                        else:
                            subject = f"Falta apenas um dia para o prazo de {coordination_exams_count} caderno(s) encerrar"
                        
                    template = get_template('mail_template/send_to_coordinators_elaboration_deadline.html')
                    
                    html = template.render({ 
                        "name": user.name, 
                        "exams_count": coordination_exams_count, 
                        "deadline": deadline, 
                        "BASE_URL": settings.BASE_URL,
                        "after_expiration": after_expiration,
                        "diff_days": diff_days,
                        
                    })
                    subject = subject
                    to = [user.email]
                    EmailThread(subject, html, to).start()
                    
                    return

    def handle(self, *args: Any, **options: Any):
        now = timezone.localtime(timezone.now())
        
        config_notifications = ConfigNotification.objects.filter(client__status=Client.ACTIVED)
        
        for config in config_notifications:
            
            deadline_first_notification_coordination = (now + timedelta(days=(config.coordination_first_notification + 1))).date()
            deadline_second_notification_coordination = (now + timedelta(days=(config.coordination_second_notification + 1))).date() if config.coordination_second_notification else None
            deadline_after_expiration_coordination = (now - timedelta(days=(config.coordination_after_expiration + 1))).date()
            
            deadline_first_notification_teacher = (now + timedelta(days=(config.first_notification + 1))).date()
            deadline_second_notification_teacher = (now + timedelta(days=(config.second_notification + 1))).date() if config.second_notification else None
            deadline_after_expiration_teacher = (now - timedelta(days=(config.after_expiration + 1))).date()
            
            # COORDINATIONS AFTER EXPIRE
            deadlines_objects = {
                "coordinators": {
                    "after_expiration": [deadline_after_expiration_coordination],
                    "before_expiration": [deadline_first_notification_coordination, deadline_second_notification_coordination]
                },
                "teachers": {
                    "after_expiration": [deadline_after_expiration_teacher],
                    "before_expiration": [deadline_first_notification_teacher, deadline_second_notification_teacher]
                }
            }
            
            # COORDINATORS
            if config.coordination_send_notification:
                for deadline in deadlines_objects['coordinators']['after_expiration']:
                    self.send_notification_to_coordination(config=config, deadline=deadline, after_expiration=True)
                for deadline in deadlines_objects['coordinators']['before_expiration']:
                    self.send_notification_to_coordination(config=config, deadline=deadline, after_expiration=False)
            
            # TEACHERS
            if config.send_notification:
                for deadline in deadlines_objects['teachers']['after_expiration']:
                    self.send_notification_to_teachers(config=config, deadline=deadline, after_expiration=True)
                for deadline in deadlines_objects['teachers']['before_expiration']:
                    self.send_notification_to_teachers(config=config, deadline=deadline, after_expiration=False)