from datetime import datetime

from django.utils import timezone
from django.core.management.base import BaseCommand
from django.db.models import F

from fiscallizeon.applications.models import ApplicationStudent

class Command(BaseCommand):
    help = 'Adiciona hora de término appication students não finaizados. Por padrão, utiliza-se a hora final da aplicação'

    def handle(self, *args, **kwargs):
        print("# Iniciando ajuste de application students não finalizados")
        today =  today = timezone.localtime(timezone.now()).date()
        application_students = ApplicationStudent.objects.filter(
            start_time__isnull=False,
            end_time__isnull=True,
            application__date__lt=today,
        )
        
        for application_student in application_students:
            print(f'- Ajustando application student {application_student.pk}')
            end_time = datetime.combine(
                application_student.application.date,
                application_student.application.end
            )
            application_student.end_time = timezone.make_aware(end_time)
            application_student.save()
        