from rest_framework import serializers

from fiscallizeon.omrnps.models import TeacherOrder, TeacherAnswer
from fiscallizeon.omrnps.serializers.teacher_answer import TeacherAnswerSerializer

class TeacherOrderSerializer(serializers.ModelSerializer):
    teacher_answers = serializers.SerializerMethodField()
    teacher_name = serializers.CharField(source='teacher_subject.teacher.name')
    subject_name = serializers.CharField(source='teacher_subject.subject.name')

    class Meta:
        model = TeacherOrder
        exclude = ['created_at', 'updated_at']

    def get_teacher_answers(self, obj):
        answers = TeacherAnswer.objects.filter(
            teacher=obj,
            omr_nps_page=self.context.get('nps_page', None),
        ).order_by(
            'nps_application_axis__order'
        )

        return TeacherAnswerSerializer(answers, many=True).data