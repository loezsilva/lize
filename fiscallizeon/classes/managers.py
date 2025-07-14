from django.db import models
from django.apps import apps
from django.utils import timezone
from django.db.models import Q

class SchoolClassQueryset(models.QuerySet):
    
    # Filtra as turmas envolvidas com as aplicações
    def filter_by_applications(self, applications):
        SchoolClass = apps.get_model('classes', 'SchoolClass')
        Student = apps.get_model('students', 'Student')

        avulse_students = Student.objects.filter(
            applications__in=applications,
        ).exclude(
            applicationstudent__student__classes__in=SchoolClass.objects.filter(
                applications__in=applications.values('pk'),
            )
        ).distinct()

        applications_school_classes = self.filter(
            Q(temporary_class=False),
            Q(school_year=timezone.now().year),
            Q(
                applications__in=applications,
            ) | Q(
                students__in=avulse_students,
            )
        ).distinct()

        return applications_school_classes


SchoolClassManager = models.Manager.from_queryset(SchoolClassQueryset)