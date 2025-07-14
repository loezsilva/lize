from statistics import fmean
from rest_framework import serializers
from django.core.cache import cache

from fiscallizeon.clients.models import Unity
from fiscallizeon.exams.models import Exam
from fiscallizeon.subjects.models import Subject

class UnityPerformanceSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='__str__')
    performance = serializers.SerializerMethodField()
    histogram = serializers.SerializerMethodField()

    class Meta:
        model = Unity
        fields = ['id', 'name', 'performance', 'histogram']
    
    def get_performance(self, obj):
        exam = Exam.objects.get(pk=obj.exam_pk)
        CACHE_KEY = f'get-performance-unity-{obj.pk}-{exam.pk}'
        
        if obj.subject_pk:
            CACHE_KEY += f'-{obj.subject_pk}'
            if not cache.get(CACHE_KEY):
                applications_student = exam.get_application_students_started().filter(
                    student__classes__coordination__unity=obj,
                )
                subject = Subject.objects.get(pk=obj.subject_pk)
                performances = [application_student.get_performance(subject=subject) for application_student in applications_student]
                cache.set(CACHE_KEY, float(fmean(performances) if performances else 0), 4 * 60 * 60)
            return cache.get(CACHE_KEY)
        
        if obj.bncc_pk:
            CACHE_KEY += f'-{obj.bncc_pk}'
            if not cache.get(CACHE_KEY):
                applications_student = exam.get_application_students_started().filter(
                    student__classes__coordination__unity=obj,
                )
                performances = [application_student.get_performance(bncc_pk=obj.bncc_pk) for application_student in applications_student]
                cache.set(CACHE_KEY, float(fmean(performances) if performances else 0), 4 * 60 * 60)
            return cache.get(CACHE_KEY)
        
        return 0
    
    def get_histogram(self, obj):
        exam = Exam.objects.get(pk=obj.exam_pk)
        CACHE_KEY = f'get-histogram-unity-{obj.pk}-{exam.pk}'
        
        if obj.subject_pk:
            CACHE_KEY+= f'-{obj.subject_pk}'
        elif obj.bncc_pk:
            CACHE_KEY+= f'-{obj.bncc_pk}'

        if not cache.get(CACHE_KEY):
            applications_student = exam.get_application_students_started().filter(
                student__classes__coordination__unity=obj,
            )
            students_count = applications_student.count()
            performances = [0, 0, 0, 0, 0]
            histogram: object = {
                "data": [],
                "categories": ['0% - 20%', '21% - 40%', '41% - 60%', '61% - 80%', '81% - 100%']
            }
            
            for application_student in applications_student:
                if obj.subject_pk:
                    subject = Subject.objects.get(pk=obj.subject_pk)
                    student_performance = application_student.get_performance(subject=subject)
                elif obj.bncc_pk:
                    student_performance = application_student.get_performance(bncc_pk=obj.bncc_pk)
                    
                if student_performance <= 20:
                    performances[0] = performances[0] + 1
                elif student_performance <= 40:
                    performances[1] = performances[1] + 1
                elif student_performance <= 60:
                    performances[2] = performances[2] + 1
                elif student_performance <= 80:
                    performances[3] = performances[3] + 1
                elif student_performance <= 100:
                    performances[4] = performances[4] + 1

            histogram['data'] = [(performances[0] / students_count) * 100, (performances[1] / students_count) * 100, (performances[2] / students_count) * 100, (performances[3] / students_count) * 100, (performances[4] / students_count) * 100]
            cache.set(CACHE_KEY, histogram, 2*60*60)
        
        return cache.get(CACHE_KEY)