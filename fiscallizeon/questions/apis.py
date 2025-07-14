from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404
from rest_framework import status

from djangorestframework_camel_case.parser import CamelCaseJSONParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from fiscallizeon.core.utils import CheckHasPermission
from fiscallizeon.exams.models import ExamQuestion
from django.conf import settings

from .models import Question, QuestionOption

from fiscallizeon.questions.models import (
    Topic, Abiliity, Competence
)
from fiscallizeon.core.api import CsrfExemptSessionAuthentication

class QuestionDetailApi(LoginRequiredMixin, CheckHasPermission, APIView):
    """
    Esta API é de uso exclusivo dos alunos, e após ele responder a questão
    Caso o aluno ainda não tenha respondido a questão, esta API deve retornar um 404
    """
    required_permissions = [settings.STUDENT]
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)

    class OutputSerializer(serializers.Serializer):
        id = serializers.CharField()
        enunciation = serializers.CharField()
        alternatives = serializers.SerializerMethodField()
        answer = serializers.SerializerMethodField()
        topics = serializers.SerializerMethodField()
        abilities = serializers.SerializerMethodField()
        competences = serializers.SerializerMethodField()
        commented_awnser = serializers.CharField()
        embbeded_answer_video = serializers.CharField(source='get_emmbbeded_video_answer')
        feedback = serializers.CharField()
        
        class TopicSerializer(serializers.ModelSerializer):
            class Meta:
                model = Topic
                fields = ('id', 'name')

        class AbiliitySerializer(serializers.ModelSerializer):
            class Meta:
                model = Abiliity
                fields = ('id', 'text')

        class CompetenceSerializer(serializers.ModelSerializer):
            class Meta:
                model = Competence
                fields = ('id', 'text')
        
        class AlternativeSerializer(serializers.ModelSerializer):
            class Meta:
                model = QuestionOption
                fields = ('id', 'text', 'is_correct')

        def get_alternatives(self, obj):
            if obj.category != Question.CHOICE:
                return []

            return self.AlternativeSerializer(obj.alternatives.distinct(), many=True).data

        def get_answer(self, obj):
            return obj.alternatives.filter(is_correct=True).last().pk
        
        def get_topics(self, obj):
            return self.TopicSerializer(
                obj.topics.distinct(), many=True
            ).data

        def get_abilities(self, obj):
            return self.AbiliitySerializer(
                obj.abilities.distinct(), many=True
            ).data

        def get_competences(self, obj):
            return self.CompetenceSerializer(
                obj.competences.distinct(), many=True
            ).data

    def get(self, request, question_id):
        
        applications_student = self.request.user.student.get_finished_application_student()
        
        queryset = Question.objects.filter(
            alternatives__optionanswer__student_application__in=applications_student,
        )
        
        question = get_object_or_404(queryset, pk=question_id)

        serializer = self.OutputSerializer(question)

        return Response(serializer.data)


class QuestionVerySimpleAPI(LoginRequiredMixin, CheckHasPermission, APIView):
    """
    Esta API é de uso exclusivo dos alunos, e após ele responder a questão
    Caso o aluno ainda não tenha respondido a questão, esta API deve retornar um 404
    """
    required_permissions = [settings.TEACHER, settings.COORDINATION]
    
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    def post(self, request):
        ids = request.data
        
        class OutputSerializer(serializers.ModelSerializer):
            enunciation_text = serializers.CharField(source='get_enunciation_str')
            
            class Meta:
                model = Question
                fields = ['id', 'enunciation_text']
                
        questions = Question.objects.filter(pk__in=ids)
        
        return Response(OutputSerializer(instance=questions, many=True).data)