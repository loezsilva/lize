from django.db import models
from django.db.models import Subquery, OuterRef
from django.apps import apps
from django.utils import timezone

class StudentQuerySet(models.QuerySet):

    def add_last_class(self):
        SchoolClass = apps.get_model('classes', 'SchoolClass')
        current_year = timezone.now().year
        
        return self.annotate(
            last_class=Subquery(
                SchoolClass.objects.filter(
                    students=OuterRef('pk'),
                    temporary_class=False,
                    school_year=current_year
                ).order_by('-created_at').values('pk')[:1]
            ),
            last_class_grade=Subquery(
                SchoolClass.objects.filter(
                    pk=OuterRef('last_class'),
                ).values('grade__pk')[:1]
            ),
            last_class_coordination=Subquery(
                SchoolClass.objects.filter(
                    pk=OuterRef('last_class'),
                ).values('coordination__pk')[:1]
            )
        ).distinct()

    def filter_by_class(self, school_class):
        return self.filter(
            classes__in=[school_class],
            classes__temporary_class=False,
            classes__school_year=timezone.now().year,
        ).distinct()

    def filter_by_coordination(self, school_coordination):
        return self.filter(
            classes__coordination=school_coordination,
            classes__temporary_class=False,
            classes__school_year=timezone.now().year,
        ).distinct()

    def filter_by_grade(self, grade):
        return self.filter(
            classes__grade=grade
        ).distinct()

StudentManager = models.Manager.from_queryset(StudentQuerySet)