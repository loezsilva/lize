from rest_framework import serializers

from fiscallizeon.answers.models import TextualAnswer
from fiscallizeon.answers.mixins import SaveRestrictionMixin, SaveRestrictionUserMixin
from fiscallizeon.applications.serializers.application_student import ApplicationStudentSimpleSerializer
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import Q
from django.db.models.functions import Length

class TextualAnswerSerializer(SaveRestrictionUserMixin, serializers.ModelSerializer):
    class Meta:
        model = TextualAnswer
        fields = '__all__'

    def validate(self, attrs):
        if (attrs['student_application'].already_reached_max_time_finish):
            raise serializers.ValidationError('O tempo máximo para finalizar essa lista de exercício foi atingido.')

        return attrs

    def save(self, **kwargs):
        if not self.instance:
            validated_data = {**self.validated_data, **kwargs}
            answer = TextualAnswer.objects.filter(
                question=validated_data.get('question'),
                student_application=validated_data.get('student_application')
            )

            if answer.exists():
                return TextualAnswerSerializer(instance=answer)

        return super(TextualAnswerSerializer, self).save(**kwargs)


class TextualAnswerDetailedNoSimilarSerializer(serializers.ModelSerializer):
    student_application = ApplicationStudentSimpleSerializer()
    similarity = serializers.DecimalField(max_digits=10, decimal_places=7)

    class Meta:
        model = TextualAnswer
        fields = ('id', 'content', 'teacher_feedback', 'teacher_grade', 'student_application', 'similarity')


class TextualAnswerDetailedSerializer(serializers.ModelSerializer):
    student_application = ApplicationStudentSimpleSerializer()
    similar_answers = serializers.SerializerMethodField()

    class Meta:
        model = TextualAnswer
        fields = ('id', 'content', 'teacher_feedback', 'teacher_grade', 'student_application', 'similar_answers')

    def get_similar_answers(self, instance):

        similar_answers = TextualAnswer.objects.none()

        LIMIT_CONTENT_SIZE = 30

        if instance.content and len(instance.content) > LIMIT_CONTENT_SIZE:            
            similar_answers = TextualAnswer.objects.annotate(
                content_lenght=Length('content')
            ).filter(
                question=instance.question,
                student_application__application__exam=instance.student_application.application.exam,
                content_lenght__gt=LIMIT_CONTENT_SIZE
            ).annotate(
                content_lenght=Length('content')
            ).exclude(
                pk=instance.pk
            ).annotate(
                similarity=TrigramSimilarity('content', instance.content),
            ).filter(similarity__gt=0.8).order_by('-similarity')

        return TextualAnswerDetailedNoSimilarSerializer(similar_answers, many=True).data 


class TextualAnswerFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = TextualAnswer
        fields = ['id', 'empty',  'question', 'student_application','teacher_feedback', 'teacher_grade', 'who_corrected', 'corrected_but_no_answer']

class TextualAnswerCreateFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = TextualAnswer
        fields = ['id', 'empty', 'question', 'student_application','teacher_feedback', 'teacher_grade', 'who_corrected', 'corrected_but_no_answer']
        

class TextualAnswerRemoveGradeSerializer(serializers.ModelSerializer):
        class Meta:
            model = TextualAnswer
            fields = ['teacher_grade', 'who_corrected', 'corrected_but_no_answer']