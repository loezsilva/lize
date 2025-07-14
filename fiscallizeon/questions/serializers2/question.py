from rest_framework import serializers

from fiscallizeon.core.utils import is_list_of_none
from ..models import Question

from fiscallizeon.subjects.serializers.topics import TopicSimpleSerializer
from fiscallizeon.bncc.serializers.ability import AbilitySimpleSerializer
from fiscallizeon.bncc.serializers.competence import CompetenceSimpleSerializer


class QuestionSerializer(serializers.ModelSerializer):
    level_description = serializers.SerializerMethodField()
    category_description = serializers.SerializerMethodField()
    alternatives_list = serializers.SerializerMethodField()
    creator = serializers.SerializerMethodField()
    topics_list = serializers.SerializerMethodField()
    abilities_list = serializers.SerializerMethodField()
    competences_list = serializers.SerializerMethodField()
    base_texts_list = serializers.SerializerMethodField()

    class Meta:
        model = Question
        fields = (
            'id',
            'level_description',
            'enunciation',
            'category_description',
            'commented_awnser',
            'feedback',
            'alternatives_list',
            'creator',
            'topics_list',
            'subject_id',
            'abilities_list',
            'competences_list',
            'adapted',
            'base_texts_list',
        )
        ref_name = 'question_v2'

    def get_level_description(self, obj):
        return obj['level_description']

    def get_category_description(self, obj):
        return obj['category_description']

    def get_alternatives_list(self, obj):
        if is_list_of_none(obj['alternatives_list']):
            return []

        return obj['alternatives_list']

    def get_creator(self, obj):
        return obj['creator']

    def get_topics_list(self, obj):
        if is_list_of_none(obj['topics_list']):
            return []

        return obj['topics_list']

    def get_abilities_list(self, obj):
        if is_list_of_none(obj['abilities_list']):
            return []

        return obj['abilities_list']

    def get_competences_list(self, obj):
        if is_list_of_none(obj['competences_list']):
            return []

        return obj['competences_list']

    def get_base_texts_list(self, obj):
        if is_list_of_none(obj['base_texts_list']):
            return []

        return obj['base_texts_list']


class QuestionVerySimpleSerializer(serializers.ModelSerializer):
    competences =  serializers.SerializerMethodField()
    abilities = serializers.SerializerMethodField()
    topics =  serializers.SerializerMethodField()
    
    
    enunciation_str = serializers.SerializerMethodField()
    category = serializers.CharField(source="get_category_display", max_length=50)
    level = serializers.CharField(source="get_level_display", max_length=50)
    subject_name = serializers.SerializerMethodField()
    detail_url = serializers.SerializerMethodField()
    
    alternatives =  serializers.SerializerMethodField()
    
    class Meta:
        model = Question
        fields = [
            'id', 
            'enunciation', 
            'competences',
            'abilities',
            'topics', 
            'enunciation_str', 
            'category', 
            'level',
            'subject_name',
            'alternatives',
            'detail_url',
            'board'
        ]
        
    def get_subject_name(self, obj):
        name = ''
        if obj.subject:
            if obj.subject.knowledge_area:
                name += obj.subject.knowledge_area.__str__()
            name += f'- {obj.subject.name}'
        return name or "Sem disciplina"
    
    def get_enunciation_str(self, obj):
        return obj.get_enunciation_str()[:150]
    
    def get_detail_url(self, obj):
        from django.urls import reverse
        return reverse('api2:select-questions-detail', kwargs={ "pk": obj.pk })
    
    def get_competences(self, obj):
        return []
    def get_abilities(self, obj):
        return []
    def get_topics(self, obj):
        return []
    def get_alternatives(self, obj):
        return []
    


class QuestionSimpleSerializer(serializers.ModelSerializer):
    competences =  CompetenceSimpleSerializer(many=True, read_only=True)
    abilities = AbilitySimpleSerializer(many=True, read_only=True)
    topics =  TopicSimpleSerializer(many=True, read_only=True)
    
    enunciation_str = serializers.SerializerMethodField()
    category = serializers.CharField(source="get_category_display", max_length=50)
    level = serializers.CharField(source="get_level_display", max_length=50)
    subject_name = serializers.SerializerMethodField()
    detail_url = serializers.SerializerMethodField()

    alternatives = serializers.SerializerMethodField()
    
    source_question_id = serializers.SerializerMethodField()

    
    class Meta:
        model = Question
        fields = [
            'id', 
            'enunciation', 
            'competences',
            'abilities',
            'topics', 
            'enunciation_str', 
            'category', 
            'level',
            'subject_name',
            'alternatives',
            'detail_url',
            'source_question_id',
        ]
        
    def get_subject_name(self, obj):
        name = ''
        if obj.subject:
            if obj.subject.knowledge_area:
                name += obj.subject.knowledge_area.__str__()
            name += f'- {obj.subject.name}'
        return name or "Sem disciplina"
    
    def get_enunciation_str(self, obj):
        return obj.get_enunciation_str()[:150]
    
    def get_alternatives(self, question):
        if question.category == Question.CHOICE:
            return question.alternatives.distinct().values('id', 'text', 'is_correct')
        return []
    
    def get_detail_url(self, obj):
        from django.urls import reverse
        return reverse('api2:select-questions-detail', kwargs={ "pk": obj.pk })
    
    def get_source_question_id(self, obj):
        return str(obj.source_question.id) if obj.source_question else None