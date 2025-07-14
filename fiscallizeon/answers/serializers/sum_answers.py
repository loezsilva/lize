from rest_framework import serializers

        
class SumAnswerSerializer(serializers.Serializer):
    application_student = serializers.UUIDField()
    question = serializers.UUIDField()
    sum_value = serializers.IntegerField(min_value= 1)

    grade = serializers.DecimalField(max_digits=5, decimal_places=4, read_only=True)
    created_by = serializers.UUIDField(read_only=True)
    created_by_name = serializers.CharField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    sum_question_sum_value = serializers.IntegerField(read_only=True)
    checked_answers = serializers.ListField(
        child=serializers.UUIDField(),
        read_only=True
    )