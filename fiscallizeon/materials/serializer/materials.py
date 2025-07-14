from rest_framework import serializers
from fiscallizeon.materials.models import StudyMaterial

class StudyMaterialSerializer(serializers.ModelSerializer):
    subjects = serializers.SerializerMethodField()
    exam = serializers.SerializerMethodField()
    class Meta:
        model = StudyMaterial
        fields = '__all__'

    def get_subjects(self, obj):
        subjects = obj.subjects.all()
        return [{'id': subject.id, 'name': subject.name} for subject in subjects]

    def get_exam(self, obj):
        return {'id': obj.exam.id, 'name': obj.exam.name} if obj.exam else None
    
class StudyMaterialSimpleSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = StudyMaterial
        fields = ['id', 'title', 'thumbnail', 'material', 'stage', 'emphasis', 'release_material_study']

    def validate_thumbnail(self, value):        
        if value and hasattr(value, 'content_type'):
            if not value.content_type in ["image/jpeg", "image/png", "image/gif", "image/jpg", "image/webp"]:
                raise serializers.ValidationError("Arquivo de imagem inválido")
        return value