
import sys

from PIL import Image
from io import BytesIO

from django.core.files.uploadedfile import InMemoryUploadedFile
from rest_framework import serializers

from fiscallizeon.answers.models import FileAnswer
from fiscallizeon.answers.mixins import SaveRestrictionMixin, SaveRestrictionUserMixin
from fiscallizeon.applications.serializers.application_student import ApplicationStudentSimpleSerializer
from fiscallizeon.corrections.serializers.correction import (
    TextCorrectionSerializer,
)

class FileAnswerSerializer(SaveRestrictionUserMixin, serializers.ModelSerializer):
    
    class Meta:
        model = FileAnswer
        fields = '__all__'

    def save(self, **kwargs):
        if not self.instance:
            validated_data = {**self.validated_data, **kwargs}
            answer = FileAnswer.objects.filter(
                question=validated_data.get('question'),
                student_application=validated_data.get('student_application')
            )

            if answer.exists():
                return FileAnswerSerializer(instance=answer)

        return super(FileAnswerSerializer, self).save(**kwargs)


class FileAnswerQRCodeSerializer(SaveRestrictionMixin, serializers.ModelSerializer): 
    class Meta:
        model = FileAnswer
        fields = '__all__'

    def save(self, **kwargs):
        validated_data = {**self.validated_data, **kwargs}

        if not self.instance:
            answer = FileAnswer.objects.filter(
                question=validated_data.get('question'),
                student_application=validated_data.get('student_application')
            )

            if answer.exists():
                return FileAnswerQRCodeSerializer(instance=answer)

        return super(FileAnswerQRCodeSerializer, self).save(**kwargs)



class FileAnswerDetailedSerializer(serializers.ModelSerializer):
    student_application = ApplicationStudentSimpleSerializer()
    class Meta:
        model = FileAnswer
        fields = ('id', 'arquivo', 'question',  'student_application', 'teacher_feedback', 'teacher_grade', 'student_application')

class FileAnswerFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileAnswer
        fields = [
            'id', 'empty',  'question',  'student_application', 'teacher_feedback', 'teacher_grade', 
            'who_corrected', 'corrected_but_no_answer', 'ai_suggestion_accepted',
        ]
        extra_kwargs = {
            'ai_suggestion_accepted': {
                'write_only': True,
            },
        }
        
class FileAnswerCreateFeedbackSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileAnswer
        fields = ['id', 'empty', 'question', 'student_application', 'teacher_feedback', 'teacher_grade', 'who_corrected', 'corrected_but_no_answer']

class FileAnswerImgAnnotationsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileAnswer
        fields = ['img_annotations',]
        
class FileAnswerWithImgAnnotationsSerializer(serializers.ModelSerializer):
    theme = serializers.CharField(source='question.get_theme', read_only=True)
    text_correction = TextCorrectionSerializer(source='question.text_correction', read_only=True)
    file_url = serializers.FileField(source='arquivo', allow_empty_file=True)
    who_corrected = serializers.CharField(source='who_corrected.name', read_only=True)
    
    class Meta:
        model = FileAnswer
        fields = ['id', 'essay_was_corrected', 'who_corrected', 'theme', 'text_correction', 'img_annotations', 'file_url', 'teacher_feedback', 'teacher_audio_feedback', 'updated_at']

class FileAnswerTeacherCoordinationSerializer(serializers.ModelSerializer):
    
    last_modified = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = FileAnswer
        fields = '__all__'
        
class FileAnswerRemoveGradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = FileAnswer
        fields = ['corrected_but_no_answer', 'who_corrected', 'teacher_grade']