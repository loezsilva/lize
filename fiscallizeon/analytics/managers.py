from datetime import datetime

from django.db import models
from django.db.models import Q, F, Count, Subquery, OuterRef, Case, When, IntegerField, Value, Sum
from django.apps import apps



class AnalyticsQuerySet(models.QuerySet):
    def filter_request(self, request):
        queryset = self.filter(
            Q(students_quantity__gt=0),            
        )
        if request.user.is_anonymous:
            return queryset.none()
        
        queryset = self.filter(
            Q(school_class__coordination__in=request.user.get_coordinations()) |
            Q(application__applicationstudent__student__client__in=request.user.get_clients())
        )

        school_classes = request.GET.getlist("q_classes")
        stage = request.GET.get("q_stage", None)
        unitys = request.GET.getlist('q_unitys')
        grades = request.GET.getlist('q_grades')
        subjects = request.GET.getlist('q_subjects')
        stage = request.GET.getlist('q_stage')
        initial_date = request.GET.get('q_initial_date', None)
        final_date = request.GET.get('q_final_date', None)

        if initial_date and not final_date: 
            queryset = queryset.filter(
                application__date=initial_date
            )
    
        if initial_date and final_date: 
            queryset = queryset.filter(
                application__date__range=(initial_date, final_date)
            )

        if school_classes and not school_classes[0] == '':
            queryset = queryset.filter(
                school_class__in=school_classes
            )

        if stage and not stage[0] == '' or stage == 0 :
            queryset = queryset.filter(
                school_class__grade__level=int(stage[0])
            )

        if unitys and not unitys[0] == '':
            queryset = queryset.filter(
                school_class__coordination__unity__in=unitys
            )

        if grades and not grades[0] == '':
            queryset = queryset.filter(
                school_class__grade__in=grades
            )

        if subjects and not subjects[0] == '':
            queryset = queryset.filter(
                teacher_subject__subject__in=subjects
            )

        return queryset

    def get_performance(self, request):

        return self.filter_request(request=request).filter(
            students_quantity__gt=0
        ).distinct().annotate(
            multiplied=F('performance')*F('students_quantity')
        ).aggregate(
            total=Sum('multiplied')/Sum('students_quantity')
        ).get('total', 0)
        
AnalyticsManager = models.Manager.from_queryset(AnalyticsQuerySet)