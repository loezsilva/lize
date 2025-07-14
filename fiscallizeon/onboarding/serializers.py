from rest_framework import serializers


class ImportCoordinatorSerializer(serializers.Serializer):
    file = serializers.FileField()


class ImportTeacherSerializer(serializers.Serializer):
    file = serializers.FileField()
    replace_coordinations = serializers.BooleanField()
    replace_subjects = serializers.BooleanField()
    replace_permissions = serializers.BooleanField()
    teachers_emails = serializers.ListField(child=serializers.EmailField())
