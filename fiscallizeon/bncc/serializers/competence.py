from statistics import fmean
from rest_framework import serializers
from fiscallizeon.applications.models import ApplicationStudent
from django.db.models import Q
from fiscallizeon.subjects.models import Grade
from fiscallizeon.bncc.models import Competence
from fiscallizeon.exams.models import Exam

class CompetenceSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competence
        fields = ("id", "code", "text")
        

class CompetenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competence
        exclude = ('client', 'created_at', 'updated_at')
        
        
class CompetenceViewSetSerializer(serializers.ModelSerializer):
    performance = serializers.SerializerMethodField()
    
    class Meta:
        model = Competence
        fields = ('id', 'performance', 'text')
        
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


class CompetenceCreateApiSerializer(serializers.ModelSerializer):
    class Meta:
        model = Competence
        exclude = ('client', 'created_at', 'updated_at')

    def validate(self, data):
        code = data.get('code')
        client = self.context['request'].user.get_clients().first()

        if code:
             if Competence.objects.filter(
                        code=code,
                        client=client,
                        subject=data.get('subject'),
                        knowledge_area=data.get('knowledge_area')
                    ).exists():
                        raise serializers.ValidationError("Esta competência já existe com os mesmos atributos.")

        else:
            text = data.get('text')
            if Competence.objects.filter(
                        text=text,
                        client=client,
                        subject=data.get('subject'),
                        knowledge_area=data.get('knowledge_area')
                    ).exists():
                        raise serializers.ValidationError("Esta competência já existe com os mesmos atributos.")

        return data