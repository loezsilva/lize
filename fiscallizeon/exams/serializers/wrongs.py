from rest_framework import serializers
from fiscallizeon.answers.models import FileAnswer, OptionAnswer, TextualAnswer
from fiscallizeon.answers.serializers.file_answers import FileAnswerDetailedSerializer
from fiscallizeon.answers.serializers.option_answers import OptionAnswerDetailedSerializer
from fiscallizeon.answers.serializers.textual_answers import TextualAnswerDetailedSerializer
from fiscallizeon.exams.models import Wrong
from fiscallizeon.exams.serializers.exam_questions import ExamQuestionAnswersSerializer
from fiscallizeon.questions.models import Question

class ExamQuestionWrongSerializer(ExamQuestionAnswersSerializer):
    
    def get_answers(self, obj):
        student = self.context['student']
        if not student:
            return []
            
        if obj.question.category == Question.CHOICE:
            answers = OptionAnswer.objects.filter(
                status=OptionAnswer.ACTIVE,
                question_option__question=obj.question,
                student_application__student=student
            ).order_by('student_application__student__name')
            return OptionAnswerDetailedSerializer(answers, many=True).data

        if obj.question.category == Question.FILE:
            answers = FileAnswer.objects.filter(
                question=obj.question,
                student_application__student=student
            ).order_by('student_application__student__name')
            return FileAnswerDetailedSerializer(answers, many=True).data

        if obj.question.category == Question.TEXTUAL:
            answers = TextualAnswer.objects.filter(
                question=obj.question,
                student_application__student=student
            ).order_by('student_application__student__name')

            return TextualAnswerDetailedSerializer(answers, many=True).data

class WrongSerializerCreate(serializers.ModelSerializer):
    class Meta:
        model = Wrong
        fields = 'exam_question', 'student', 'student_description', 'status'

class WrongSerializer(serializers.ModelSerializer):
    status_name = serializers.CharField(source='get_status_display')
    teacher_name = serializers.SerializerMethodField()
    exam_question = ExamQuestionWrongSerializer(many=False, read_only=True)

    class Meta:
        model = Wrong
        fields = '__all__'
    
    def get_teacher_name(self, obj):
        return obj.user.name if obj.user else ''

class StudentWrongResendSerializerUpdate(serializers.ModelSerializer):

    class Meta:
        model = Wrong
        fields = ['student_description', 'status', 'updated_at']