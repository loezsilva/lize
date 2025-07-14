from rest_framework import serializers

from ..models import ExamTeacherSubject
from fiscallizeon.exams.serializers.exams import ExamTeacherTeacherSubjectSerializer, ExamQuestionTeacherSerializer
from fiscallizeon.questions.serializers2.question import QuestionSimpleSerializer

class ExamTeacherSubjectSerializer(serializers.ModelSerializer):
    teacher_id = serializers.SerializerMethodField()
    subject_id = serializers.SerializerMethodField()

    class Meta:
        model = ExamTeacherSubject
        fields = (
            'id',
            'teacher_id',
            'exam_id',
            'quantity',
            'note',
            'teacher_note',
            'subject_id',
        )

    def get_teacher_id(self, obj):
        return obj['teacher_id']

    def get_subject_id(self, obj):
        return obj['subject_id']

class ExamTeacherTeacherSubjectViewQuestionsSerializer(ExamTeacherTeacherSubjectSerializer):
    class ExamQuestionTeacherViewQuestionSerializer(ExamQuestionTeacherSerializer):
        question = QuestionSimpleSerializer(many=False)
    
    questions  = ExamQuestionTeacherViewQuestionSerializer(source="examquestion_set", many=True)