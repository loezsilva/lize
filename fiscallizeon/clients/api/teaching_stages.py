from rest_framework import viewsets
from rest_framework import serializers
from fiscallizeon.clients.models import TeachingStage
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from djangorestframework_camel_case.parser import CamelCaseJSONParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from fiscallizeon.core.utils import CheckHasPermissionAPI

class TeachingStageViewSet(viewsets.ModelViewSet, CheckHasPermissionAPI):
    class InputSerializer(serializers.ModelSerializer):
        urls = serializers.SerializerMethodField()
        class Meta:
            model = TeachingStage
            fields = ['id', 'client', 'name', 'urls', 'code_export']
            
        def get_urls(self, obj):
            return obj.urls
        
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    serializer_class = InputSerializer
    authentication_classes = (CsrfExemptSessionAuthentication,)
    queryset = TeachingStage.objects.none()
    
    class UpdateSerializer(serializers.ModelSerializer):
        
        class Meta:
            model = TeachingStage
            exclude = ['client']
    
    def get_queryset(self):
        queryset = TeachingStage.objects.filter(client__in=self.request.user.get_clients_cache()).distinct()
        return queryset
    
    def get_serializer_class(self):
        if self.request.method == 'PUT' or self.request.method == 'PATCH':
            return self.UpdateSerializer
        
        return super().get_serializer_class()