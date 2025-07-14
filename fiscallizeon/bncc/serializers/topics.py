from statistics import fmean
from rest_framework import serializers
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.classes.serializers import GradeSerializer
from fiscallizeon.exams.models import Exam
from fiscallizeon.subjects.models import Topic
from django.db.models import Q

class TopicSerializer(serializers.ModelSerializer):
    grades = GradeSerializer(many=True, read_only=True)

    class Meta:
        model = Topic
        exclude = ('client', 'created_at', 'updated_at')
        ref_name = "Topics"

        
class TopicViewSetSerializer(serializers.ModelSerializer):
    performance = serializers.SerializerMethodField()
    
    class Meta:
        model = Topic
        fields = ('id', 'performance', 'name')
        
    def get_performance(self, obj):
        
        from fiscallizeon.subjects.models import Subject
        
        request = self.context.get('request')
        if request and request.GET.get('get_performance'):
            user = request.user
            student = user.student
            
            if request.GET.get('subject'):
                
                subject = Subject.objects.get(pk=request.GET.get('subject'))
                obj_performance = obj.last_performance(student=student, subject=subject).first()
                return obj_performance.performance if obj_performance else 0
        
        return None