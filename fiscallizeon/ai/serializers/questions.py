from rest_framework import serializers

from fiscallizeon.subjects.serializers.topics import TopicSimpleSerializer
from fiscallizeon.bncc.serializers.ability import AbilitySimpleSerializer
from fiscallizeon.bncc.serializers.competence import CompetenceSimpleSerializer
from fiscallizeon.questions.models import QuestionOption
from ..models import QuestionImprove


class CreateAiQuestionSerializer(serializers.Serializer):
    user_prompt = serializers.CharField(max_length=4096)
    items = serializers.JSONField()
    base_image = serializers.ImageField(required=False)


class QuestionOptionAiSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ('text', 'is_correct')

class ImproveAiQuestionSerializer(serializers.Serializer):
    enunciation = serializers.CharField(max_length=4096)
    alternatives = QuestionOptionAiSerializer(many=True)

class ClassifyQuestionAbilitySerializer(serializers.Serializer):
    enunciation = serializers.CharField(max_length=4096)
    alternatives = QuestionOptionAiSerializer(many=True)
    grade = serializers.UUIDField()
    subjects = serializers.ListField(child=serializers.UUIDField(), required=False)
    knowledge_area = serializers.UUIDField(required=False)
    limit = serializers.IntegerField(min_value=1, max_value=10, required=False)

class ClassifyQuestionCompetenceSerializer(serializers.Serializer):
    enunciation = serializers.CharField(max_length=4096)
    alternatives = QuestionOptionAiSerializer(many=True)
    subjects = serializers.ListField(child=serializers.UUIDField(), required=False)
    knowledge_area = serializers.UUIDField(required=False)
    limit = serializers.IntegerField(min_value=1, max_value=10, required=False)

class ClassifyQuestionTopicSerializer(serializers.Serializer):
    enunciation = serializers.CharField(max_length=4096)
    alternatives = QuestionOptionAiSerializer(many=True)
    grade = serializers.UUIDField(required=False)
    subjects = serializers.ListField(child=serializers.UUIDField(), required=False)
    limit = serializers.IntegerField(min_value=1, max_value=10, required=False)

class QuestionImproveSerializer(serializers.ModelSerializer):

    competences =  CompetenceSimpleSerializer(many=True, read_only=True)
    abilities = AbilitySimpleSerializer(many=True, read_only=True)
    topics =  TopicSimpleSerializer(many=True, read_only=True)
    available_to_show = serializers.BooleanField()
    enunciation_status_display = serializers.CharField(source="get_enunciation_status_display")
    commented_answer_status_display = serializers.CharField(source="get_commented_answer_status_display")
    topics_status_display = serializers.CharField(source="get_topics_status_display")
    abilities_status_display = serializers.CharField(source="get_abilities_status_display")
    competences_status_display = serializers.CharField(source="get_competences_status_display")
    liked_enunciation_display = serializers.CharField(source="get_liked_enunciation_display")
    liked_commented_answer_display = serializers.CharField(source="get_liked_commented_answer_display")
    liked_topics_display = serializers.CharField(source="get_liked_topics_display")
    liked_abilities_display = serializers.CharField(source="get_liked_abilities_display")
    liked_competences_display = serializers.CharField(source="get_liked_competences_display")

    class Meta:
        model = QuestionImprove
        fields = '__all__'

class QuestionImproveSimpleSerializer(serializers.ModelSerializer):

    class Meta:
        model = QuestionImprove
        fields = [
            'enunciation_status', 
            'commented_answer_status', 
            'topics_status', 
            'abilities_status', 
            'competences_status', 
            'liked_enunciation', 
            'liked_commented_answer', 
            'liked_topics', 
            'liked_abilities', 
            'liked_competences',
            'applied_topics', 
            'applied_abilities', 
            'applied_competences',
        ]

class CorrectDiscursiveQuestionSerializer(serializers.Serializer):
    grade = serializers.DecimalField(max_digits=3, decimal_places=2, allow_null=True)
    teacher_feedback = serializers.CharField(allow_null=True)