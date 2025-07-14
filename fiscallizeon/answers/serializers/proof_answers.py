from rest_framework import serializers

from fiscallizeon.answers.models import ProofAnswer
from fiscallizeon.answers.mixins import SaveRestrictionUserMixin

class ProofAnswerSimpleSerializer(SaveRestrictionUserMixin, serializers.ModelSerializer):
    student_name = serializers.CharField(source="application_student.student.name")
    class Meta:
        model = ProofAnswer
        fields = ['id', 'code', 'student_name']