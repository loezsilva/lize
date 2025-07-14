from rest_framework import serializers
from fiscallizeon.applications.models import ApplicationStudent
from fiscallizeon.subjects.models import Grade
from fiscallizeon.bncc.models import Abiliity
from fiscallizeon.classes.serializers import GradeSerializer
from django.db.models import Q

from fiscallizeon.exams.models import Exam

class AbilitySimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Abiliity
        fields = ("id", "text", "code")
        
class AbilitySerializer(serializers.ModelSerializer):
    grades = GradeSerializer(many=True, read_only=True)
    class Meta:
        model = Abiliity
        exclude = ('client', 'created_at', 'updated_at')
        
class AbilitySerializerAnilytics(serializers.ModelSerializer):
    knowledge_object = serializers.SerializerMethodField() 
    class Meta:
        model = Abiliity
        fields = ("id", "text", "knowledge_object",  "code")
        
    def get_knowledge_object(self, obj):
        return obj.knowledge_object.text if obj.knowledge_object else ''
    

class AbilityViewSetSerializer(serializers.ModelSerializer):
    performance = serializers.SerializerMethodField()
    
    class Meta:
        model = Abiliity
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
    

class AbilityCreateApiSerializer(serializers.ModelSerializer):
    class Meta:
        model = Abiliity
        exclude = ('client', 'created_at', 'updated_at')

    def validate(self, data):
        code = data.get('code')
        grades = data.get('grades')[0]
        client = self.context['request'].user.get_clients().first()

        if Abiliity.objects.filter(
            code=code,
            client=client,
            subject=data.get('subject'),
            grades=grades
        ).exists():
            raise serializers.ValidationError("Esta habilidade já existe com os mesmos atributos.")

        return data