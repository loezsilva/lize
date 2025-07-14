from datetime import datetime

from rest_framework import serializers

from fiscallizeon.applications.models import Application
from fiscallizeon.exams.models import Exam, ExamQuestion, ExamTeacherSubject
from fiscallizeon.questions.models import BaseText, Question, QuestionOption
from fiscallizeon.subjects.models import KnowledgeArea


class QuestionOptionSerializer(serializers.ModelSerializer):
    content = serializers.CharField(source='text')

    class Meta:
        model = QuestionOption
        fields = (
          'id',
          'content',
        )


class QuestionSerializer(serializers.ModelSerializer):
    number = serializers.SerializerMethodField()
    category_display = serializers.CharField(source='get_category_display')
    alternatives = QuestionOptionSerializer(many=True)

    class Meta:
        model = Question
        fields = (
          'id',
          'number',
          'enunciation',
          'category',
          'category_display',
          'base_texts',
          'alternatives',
        )

    def get_number(self, obj):
        return 1


class BaseTextSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaseText
        fields = (
          'id',
          'text',
        )


class ExamQuestionSerializer(serializers.ModelSerializer):
    # question = QuestionSerializer()
    number = serializers.SerializerMethodField()
    enunciation = serializers.CharField(source='question.enunciation')
    category = serializers.IntegerField(source='question.category')
    category_display = serializers.CharField(source='question.get_category_display')
    base_texts = BaseTextSerializer(many=True, source='question.base_texts')
    alternatives = QuestionOptionSerializer(many=True, source='question.alternatives')

    class Meta:
        model = ExamQuestion
        fields = (
          # 'id',
          # 'question',
          'id',
          'number',
          'enunciation',
          'category',
          'category_display',
          'base_texts',
          'alternatives',
        )

    def get_number(self, obj):
        return 1


# class ExamSerializer(serializers.ModelSerializer):
#     questions = ExamQuestionSerializer(many=True, source='examquestion_set')

#     class Meta:
#         model = Exam
#         fields = (
#           'id',
#           'name',
#           'questions',
#         )


class KnowledgeAreaSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeArea
        fields = (
          'id',
          'name',
        )


class ExamTeacherSubjectSerializer(serializers.ModelSerializer):
    # name = serializers.CharField(source='teacher_subject.subject.name')
    # questions = ExamQuestionSerializer(many=True, source='examquestion_set')
    # knowledge_area = KnowledgeAreaSerializer(source='teacher_subject.subject.knowledge_area')

    class Meta:
        model = ExamTeacherSubject
        fields = (
          'id',
          # 'name',
          # 'is_foreign_language',
          # 'knowledge_area',
          # 'questions',
        )


class ApplicationSerializer(serializers.ModelSerializer):
    # exam = ExamSerializer()
    name = serializers.CharField(source='exam.name')
    # questions = ExamQuestionSerializer(many=True, source='exam.examquestion_set')
    subjects = ExamTeacherSubjectSerializer(many=True, read_only=True, source='exam.examteachersubject_set')
    start_date = serializers.SerializerMethodField()
    end_date = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = (
          'id',
          'name',
          'start_date',
          'end_date',
          'subjects',
        )

    def get_start_date(self, obj):
        return datetime.combine(obj.date, obj.start)

    def get_end_date(self, obj):
        return datetime.combine(obj.date, obj.end)
