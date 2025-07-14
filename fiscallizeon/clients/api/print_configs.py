from rest_framework import viewsets
from rest_framework import serializers
from fiscallizeon.clients.models import ExamPrintConfig
from rest_framework.response import Response
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from djangorestframework_camel_case.parser import CamelCaseJSONParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from fiscallizeon.core.utils import CheckHasPermissionAPI
from rest_framework.decorators import action

class ExamPrintConfigViewSet(viewsets.ModelViewSet, CheckHasPermissionAPI):
    class OutputSerializer(serializers.ModelSerializer):
        urls = serializers.SerializerMethodField()
        header = serializers.SerializerMethodField()
        background_image = serializers.SerializerMethodField()
        
        class Meta:
            model = ExamPrintConfig
            exclude = ['created_at', 'updated_at']
            ref_name = 'create_exam_print_config'
            
        def get_urls(self, obj):
            return obj.urls

        def get_header(self, obj):
            return str(obj.header.pk) if obj.header else ""
        
        def get_background_image(self, obj):
            return str(obj.background_image.pk) if obj.background_image else ""
        
    class SimplePrintConfigSerializer(serializers.ModelSerializer):
        urls = serializers.JSONField()
        class Meta:
            model = ExamPrintConfig
            fields = ['id', 'name', 'urls']
            ref_name = 'simple_exam_print_config'

    class UpdateSerializer(serializers.ModelSerializer):
        
        class Meta:
            model = ExamPrintConfig
            exclude = ['client']
            ref_name = 'update_exam_print_config'
            
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    serializer_class = OutputSerializer
    authentication_classes = (CsrfExemptSessionAuthentication,)
    queryset = ExamPrintConfig.objects.none()
    
    def get_queryset(self):
        queryset = ExamPrintConfig.objects.filter(
            client=self.request.user.client, is_default=True, exams__isnull=True
        ).exclude(
            name__startswith="Configuração "
        ).distinct()
        
        return queryset
    
    def get_serializer_class(self):
        if self.request.method == 'PUT' or self.request.method == 'PATCH':
            return self.UpdateSerializer
        return super().get_serializer_class()
    
    @action(detail=True, methods=["GET"])
    def get_config(self, request, pk=None):
        
        exam_print_config = ExamPrintConfig.objects.get(pk=pk, client=self.request.user.client)

        return Response(self.OutputSerializer(instance=exam_print_config).data)