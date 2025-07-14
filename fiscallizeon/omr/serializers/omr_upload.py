from django.core.validators import FileExtensionValidator

from rest_framework import serializers

from fiscallizeon.omr.models import OMRCategory, OMRStudents, OMRUpload


class OMRUploadStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OMRUpload
        fields = ('id', 'status')

    
class OMRStudentsStatusSerializer(serializers.ModelSerializer):
    history = serializers.SerializerMethodField()

    class Meta:
        model = OMRStudents
        fields = ('history', )
    
    def get_history(self, obj):
        historical = []
        for history in obj.history.all():
            if history.checked_by:
                historical.append({
                    "id": history.history_id,
                    "checked_by": history.checked_by.name if history.checked_by else '',
                    "checked": history.checked,
                    "history_date": history.history_date,
                })
        
        return historical

        
class OMRStudentsUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OMRStudents
        fields = ('checked',)


class AnswerSheetSerializer(serializers.Serializer):
    pdf_scan = serializers.FileField(
        label='Arquivo escaneado',
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])]
    )
    omr_category = serializers.PrimaryKeyRelatedField(
        label='Modelo de gabarito',
        queryset=OMRCategory.objects.all(),
        allow_null=True,
        required=False,
    )
