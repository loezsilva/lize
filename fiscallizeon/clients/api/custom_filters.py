from rest_framework import viewsets
from rest_framework import serializers
from fiscallizeon.clients.models import ClientCustomFilter
from rest_framework.response import Response
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from djangorestframework_camel_case.parser import CamelCaseJSONParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from fiscallizeon.core.utils import CheckHasPermissionAPI
from django_filters.rest_framework import DjangoFilterBackend

class ClientCustomFiltersViewSet(viewsets.ModelViewSet, CheckHasPermissionAPI):
    class InputSerializer(serializers.ModelSerializer):
        urls = serializers.SerializerMethodField()
        full_url = serializers.SerializerMethodField()
        class Meta:
            model = ClientCustomFilter
            fields = ['id', 'name', 'url', 'full_url', 'params', 'urls', 'user']
            ref_name = 'create_client_custom_filters'
            
        def get_urls(self, obj):
            return obj.urls
        
        def get_full_url(self, obj):
            from django.urls import reverse
            return reverse(obj.url) + '?' + obj.params
        
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    serializer_class = InputSerializer
    authentication_classes = (CsrfExemptSessionAuthentication,)
    queryset = ClientCustomFilter.objects.none()
    filterset_fields = ['url']
    filter_backends = [DjangoFilterBackend]
    
    class UpdateSerializer(serializers.ModelSerializer):
        
        class Meta:
            model = ClientCustomFilter
            exclude = ['user']
            ref_name = 'update_client_custom_filters'
    
    def get_queryset(self):
        queryset = ClientCustomFilter.objects.filter(user=self.request.user).distinct()
        return queryset
    
    def get_serializer_class(self):
        if self.request.method == 'PUT' or self.request.method == 'PATCH':
            return self.UpdateSerializer
        
        return super().get_serializer_class()