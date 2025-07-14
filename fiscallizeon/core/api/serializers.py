from rest_framework import serializers
from fiscallizeon.accounts.models import CustomGroup
from django.db.models import F, Value
from django.db.models.functions import Concat
from djangorestframework_camel_case.util import camelize

class CustomGroupSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()
    urls = serializers.JSONField(read_only=True)
    can_update = serializers.BooleanField(read_only=True)
    can_be_removed = serializers.SerializerMethodField()

    class Meta:
        model = CustomGroup
        fields = '__all__'
    
    def get_permissions(self, obj):
        if obj.permissions.exists():
            return obj.permissions.annotate(permission_name=Concat(F("content_type__app_label"), Value("."), F("codename"))).values_list('permission_name', flat=True)
        return []
    def get_can_be_removed(self, obj):
        return obj.can_be_removed
class CustomGroupSimpleSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    class Meta:
        model = CustomGroup
        fields = ['id', 'name']
        
    def get_name(self, obj):
        name = obj.name
        if not obj.client:
            name += ' (Lize)'
        
        return name 