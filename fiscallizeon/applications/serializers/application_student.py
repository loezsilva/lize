from rest_framework import serializers
from fiscallizeon.applications.models import ApplicationStudent
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models.functions import Length
from fiscallizeon.subjects.models import Subject
from django.db.models import Q
from django.conf import settings


class ApplicationStudentSimpleSerializer(serializers.ModelSerializer):
    student = serializers.CharField(source='student.name', default='')
    student_id = serializers.CharField(source='student.id', default='')
    
    class Meta:
        model = ApplicationStudent
        fields = ('pk', 'student', 'student_id')

class ApplicationStudentJustifyDelaySerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationStudent
        fields = ('justification_delay', )
        
class ApplicationStudentPerformanceSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='student.name')
    performance = serializers.SerializerMethodField()
    histogram = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationStudent
        fields = ['id', 'name', 'performance', 'histogram']
    
    def get_performance(self, obj):
        if obj.subject_pk:
            subject = Subject.objects.get(pk=obj.subject_pk)
            return float(obj.get_performance(subject=subject))
        if obj.bncc_pk:
            return float(obj.get_performance(bncc_pk=obj.bncc_pk))
    
    def get_histogram(self, obj):
        if obj.last_performance.first() and obj.last_performance.first().histogram:
            return obj.last_performance.first().histogram
        return None

class ClassesPerformancesSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='student.name')
    performance = serializers.SerializerMethodField()
    histogram = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationStudent
        fields = ['id', 'name', 'performance', 'histogram']
    
    def get_performance(self, obj):
        if obj.subject_pk:
            subject = Subject.objects.get(pk=obj.subject_pk)
            return float(obj.get_performance(subject=subject))
        if obj.bncc_pk:
            return float(obj.get_performance(bncc_pk=obj.bncc_pk))
    
    def get_histogram(self, obj):
        if obj.last_performance.first() and obj.last_performance.first().histogram:
            return obj.last_performance.first().histogram
        return None

class ApplicationStudentWithAnswerSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name')
    student_id = serializers.CharField(source='student.id')
    files_urls = serializers.JSONField(source='get_files_urls')
    answers = serializers.SerializerMethodField()
    similar_answers = serializers.SerializerMethodField()
    can_be_corrected = serializers.SerializerMethodField()
    
    class Meta:
        model = ApplicationStudent
        fields = ('id' , 'student_id', 'student_name', 'files_urls', 'answers', 'similar_answers', 'can_be_corrected', 'is_omr', 'missed')
        
    def get_answers(self, obj):
        answers = obj.get_answers(question=self.context.get('question') if self.context.get('question') else None)
        return answers
    
    def get_similar_answers(self, obj):
        
        from fiscallizeon.answers.models import TextualAnswer
        from fiscallizeon.answers.serializers.textual_answers import TextualAnswerDetailedNoSimilarSerializer
        
        similar_answers = TextualAnswer.objects.none()

        if self.context.get('question'):
            
            LIMIT_CONTENT_SIZE = 30
            if answer := TextualAnswer.objects.filter(student_application=obj, question=self.context.get('question')).first():

                if answer.content and len(answer.content) > LIMIT_CONTENT_SIZE:            
                    similar_answers = TextualAnswer.objects.annotate(
                        content_lenght=Length('content')
                    ).filter(
                        question=self.context.get('question'),
                        student_application=obj,
                        content_lenght__gt=LIMIT_CONTENT_SIZE
                    ).exclude(
                        id=answer.id
                    ).annotate(
                        content_lenght=Length('content')
                    ).annotate(
                        similarity=TrigramSimilarity('content', answer.content),
                    ).filter(similarity__gt=0.8).order_by('-similarity')

        return TextualAnswerDetailedNoSimilarSerializer(similar_answers, many=True).data 
    
    def get_can_be_corrected(self, obj):
        return obj.can_be_corrected(
            self.context['request'].user.inspector if self.context['request'].user.user_type == settings.TEACHER else None
        )