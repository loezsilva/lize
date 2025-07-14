from rest_framework import status, viewsets, serializers
from rest_framework.response import Response
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.integrations.models import Integration, IntegrationToken
from djangorestframework_camel_case.parser import CamelCaseJSONParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from django.contrib.auth.mixins import LoginRequiredMixin
from fiscallizeon.core.utils import CheckHasPermissionAPI
from rest_framework.generics import UpdateAPIView

class IntegrationUpdateAPIView(LoginRequiredMixin, CheckHasPermissionAPI, UpdateAPIView):
    class InputSerializer(serializers.ModelSerializer):
        class Meta:
            model = Integration
            fields = ['token']
            
    model = Integration
    queryset = Integration.objects.all()
    serializer_class = InputSerializer
    authentication_classes = (CsrfExemptSessionAuthentication, )
    
    def get_object(self):
        return self.request.user.client.integration

class IntegrationTokenSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = IntegrationToken
        fields = ['id', 'name', 'integration', 'token', 'expiration_date', 'can_delete']

class IntegrationSerializer(serializers.ModelSerializer):
    erp_display = serializers.CharField(source='get_erp_display', read_only=True)
    tokens = IntegrationTokenSerializer(read_only=True, many=True)
    
    class Meta:
        model = Integration
        fields = ['id', 'erp', 'erp_display', 'token', 'tokens', 'school_code']


class IntegrationViewSet(viewsets.ModelViewSet):
    modal = Integration
    queryset = Integration.objects.all()
    serializer_class = IntegrationSerializer
    authentication_classes = (CsrfExemptSessionAuthentication,)
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        queryset = queryset.filter(client=user.client)
        return queryset
    
    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(client=user.client)        
        instance = serializer.instance
        data = self.request.data
        
        tokens = list(filter(lambda x: x['token'], data.get('tokens')))
        
        for token_data in tokens:
            
            if not len(token_data.get('expiration_date')):
                token_data['expiration_date'] = None # Trata a data, caso venha uma string vazia
            
            token_data['integration'] = instance.id
            
            token_serializer = IntegrationTokenSerializer(data=token_data)
            token_serializer.is_valid(raise_exception=True)
            token_serializer.save()
    
    
    def perform_update(self, serializer):
        serializer.save()
        instance = serializer.instance
        data = self.request.data
        
        tokens = list(filter(lambda x: x['token'], data.get('tokens')))
        
        instance.tokens.filter(id__in=data.get('removed_tokens')).delete()
        
        if tokens:
            
            for token_data in tokens:
                
                token_id = token_data.get('id')
                token_data['integration'] = str(instance.id)
                
                if not len(token_data.get('expiration_date')):
                    token_data['expiration_date'] = None # Trata a data, caso venha uma string vazia
                
                if token_in_db := IntegrationToken.objects.filter(id=token_id).first():
                    if not token_data.get('token'):
                        token_data['token'] = token_in_db.token
                    
                    token_serializer = IntegrationTokenSerializer(instance=token_in_db, data=token_data, partial=True)
                    token_serializer.is_valid(raise_exception=True)
                    token_serializer.save()
                else:
                    token_serializer = IntegrationTokenSerializer(data=token_data)
                    token_serializer.is_valid(raise_exception=True)
                    token_serializer.save()