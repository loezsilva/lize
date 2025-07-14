from rest_framework import serializers

from fiscallizeon.answers.models import OptionAnswer
from fiscallizeon.answers.mixins import SaveRestrictionMixin, SaveRestrictionUserMixin
from fiscallizeon.applications.serializers.application_student import ApplicationStudentSimpleSerializer
from fiscallizeon.questions.models import QuestionOption


class OptionAnswerSerializer(SaveRestrictionUserMixin, serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.name', default='')
    is_correct = serializers.BooleanField(source="question_option.is_correct", read_only=True)
    teacher_grade = serializers.DecimalField(source="get_teacher_grade", max_digits=10, decimal_places=6, read_only=True)
    
    class Meta:
        model = OptionAnswer
        fields = '__all__'

    def validate(self, attrs):
        if (attrs['student_application'].already_reached_max_time_finish):
            raise serializers.ValidationError('O tempo máximo para finalizar essa lista de exercício foi atingido.')

        return attrs

    def save(self, **kwargs):
        self.validated_data['created_by'] = self.context['request'].user

        if not self.instance:
            validated_data = {**self.validated_data, **kwargs}
            question_option = validated_data.get('question_option')

            answers = OptionAnswer.objects.using('default').filter(
                question_option__question=question_option.question,
                student_application=validated_data.get('student_application')
            ).order_by(
                'created_at'
            )
            
            if answers.exists():
                last_answer = answers.last()
                if last_answer.question_option == question_option:
                    return OptionAnswerSerializer(instance=last_answer)
                else:
                    last_answer.status = OptionAnswer.INACTIVE
                    last_answer.save()

        return super(OptionAnswerSerializer, self).save(**kwargs)

class OptionAnswerWithoutAnswerSerializer(SaveRestrictionUserMixin, serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.name', default='')
    
    class Meta:
        model = OptionAnswer
        fields = '__all__'

    def validate(self, attrs):
        if (attrs['student_application'].already_reached_max_time_finish):
            raise serializers.ValidationError('O tempo máximo para finalizar essa lista de exercício foi atingido.')

        return attrs

    def save(self, **kwargs):
        self.validated_data['created_by'] = self.context['request'].user

        if not self.instance:
            validated_data = {**self.validated_data, **kwargs}
            question_option = validated_data.get('question_option')

            answers = OptionAnswer.objects.using('default').filter(
                question_option__question=question_option.question,
                student_application=validated_data.get('student_application')
            ).order_by(
                'created_at'
            )

            if answers.exists():
                last_answer = answers.last()
                if last_answer.question_option == question_option:
                    return OptionAnswerWithoutAnswerSerializer(instance=last_answer)
                else:
                    last_answer.status = OptionAnswer.INACTIVE
                    last_answer.save()

        return super(OptionAnswerWithoutAnswerSerializer, self).save(**kwargs)

class OptionAnswerSimpleSerializer(serializers.ModelSerializer):
    is_correct = serializers.SerializerMethodField()
    question = serializers.SerializerMethodField()

    class Meta:
        model = OptionAnswer
        fields = ('question_option', 'is_correct', 'question',)

    def get_is_correct(self, option_answer):
        return option_answer.question_option.is_correct

    def get_question(self, option_answer):
        return option_answer.question_option.question.pk


class OptionAnswerDetailedSerializer(serializers.ModelSerializer):
    is_correct = serializers.SerializerMethodField()
    student_application = ApplicationStudentSimpleSerializer()
    text = serializers.CharField(source='question_option.text', default='')
    class Meta:
        model = OptionAnswer
        fields = ('pk', 'question_option', 'is_correct', 'student_application', 'text')

    def get_is_correct(self, option_answer):
        return option_answer.question_option.is_correct

class QuestionOptionAnswerVerySimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionOption
        fields = ('id', 'is_correct' )