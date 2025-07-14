from rest_framework import serializers

        
class TriSerializer(serializers.Serializer):
    year = serializers.IntegerField(
        min_value=2020, 
        required=False
    )
    exams = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
        min_length=1, 
        max_length=5
    )
    school_classes = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=True,
        required=False,
        help_text="Lista com IDs de turmas"
    )
    unities = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=True,
        required=False,
        help_text="Lista com IDs de unidades"
    )
    students = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=True,
        required=False,
        help_text="Lista com IDs de students"
    )
    ignore_cache = serializers.BooleanField(default=False, required=False)


class ItemsParamsSerializer(serializers.Serializer):
    year = serializers.IntegerField(
        min_value=2020,
        required=False,
    )
    exams = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
        min_length=1, 
        max_length=5
    )


class SisuMetadataSerializer(serializers.Serializer):
    year = serializers.IntegerField(
        min_value=2022,
        max_value=2022,
    )
    states = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
        required=False,
        help_text="Lista com siglas dos estados para filtragem de metadados"
    )

class GradesSisuSerializer(serializers.Serializer):
    grade_cn = serializers.FloatField()
    grade_ch = serializers.FloatField()
    grade_mt = serializers.FloatField()
    grade_lc = serializers.FloatField()
    grade_r = serializers.FloatField()

class SisuSerializer(serializers.Serializer):
    year = serializers.IntegerField(
        min_value=2022,
    )
    grades = GradesSisuSerializer()
    waitlist = serializers.BooleanField(default=False)
    states = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
        min_length=1,
    )
    cities = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=True,
        required=False,
    )
    courses_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=True,
        required=False,
    )
    unities_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=True,
        required=False,
    )