from rest_framework import serializers
from fiscallizeon.exams.models import Exam
from fiscallizeon.questions.models import BaseText
from fiscallizeon.core.print_colors import *
class BaseTextSerializer(serializers.ModelSerializer):
    short_text = serializers.SerializerMethodField()
    urls = serializers.JSONField(read_only=True)
    can_delete = serializers.BooleanField(read_only=True)

    class Meta:
        model = BaseText
        fields = ['id', 'title', 'text', 'short_text', 'created_by', 'can_delete', 'urls']

    def get_short_text(self, obj):
        return obj.get_enunciation_str()[:200]

    # def get_questions(self, obj):
    #     from fiscallizeon.questions.serializers.questions import SimpleQuestionSerializer
    #     return SimpleQuestionSerializer(instance=Question.objects.filter(base_texts=obj).distinct(), many=True).data
        
class BaseTextSimpleSerializer(serializers.ModelSerializer):
    urls = serializers.JSONField(read_only=True)
    
    class Meta:
        model = BaseText
        fields = '__all__'

class BaseTextExamSerializer(serializers.ModelSerializer):
    base_texts = serializers.SerializerMethodField()
    
    class Meta:
        model = Exam
        fields = ['base_texts']

    def get_base_texts(self, obj):
        return BaseTextSerializer(instance=BaseText.objects.filter(question__exams=obj).distinct(), many=True).data