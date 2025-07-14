from rest_framework import viewsets
from rest_framework import serializers
from fiscallizeon.clients.models import EducationSystem, Unity
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from djangorestframework_camel_case.parser import CamelCaseJSONParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from fiscallizeon.core.utils import CheckHasPermissionAPI

class EducationSystemViewSet(viewsets.ModelViewSet, CheckHasPermissionAPI):
            
    class InputSerializer(serializers.ModelSerializer):
        class UnitiesSerializer(serializers.ModelSerializer):
            class Meta:
                model = Unity
                fields = ['id', 'name']
                
        urls = serializers.SerializerMethodField()
        selected_unities = serializers.SerializerMethodField()
        
        class Meta:
            model = EducationSystem
            fields = ['id', 'client', 'selected_unities', 'name', 'unities', 'urls']
            ref_name = 'create_education_system'
            
        def get_urls(self, obj):
            return obj.urls
        def get_selected_unities(self, obj):
            return self.UnitiesSerializer(obj.unities, many=True).data
        
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    serializer_class = InputSerializer
    authentication_classes = (CsrfExemptSessionAuthentication,)
    queryset = EducationSystem.objects.none()
    
    class UpdateSerializer(serializers.ModelSerializer):
        
        class Meta:
            model = EducationSystem
            exclude = ['client']
            ref_name = 'update_education_system'
    
    def get_queryset(self):
        queryset = EducationSystem.objects.filter(client__in=self.request.user.get_clients_cache()).distinct()
        return queryset
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return self.InputSerializer
        if self.request.method == 'PUT' or self.request.method == 'PATCH':
            return self.UpdateSerializer
        
        return super().get_serializer_class()