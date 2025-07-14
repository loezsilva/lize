from django_filters.rest_framework import DjangoFilterBackend

from rest_framework import filters, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser

from django.urls import resolve
from djangorestframework_camel_case.parser import CamelCaseJSONParser
from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from ..models import Client, ClientTeacherObligationConfiguration
from ..serializers.clients import ClientSerializer, ClientTeacherObligationConfigurationSerializer
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from rest_framework.decorators import action



class IsSuperUser(IsAdminUser):
    def has_permission(self, request, view):
        return bool(request.user and (request.user.is_superuser or request.user.is_staff))

class ClientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = (IsSuperUser,)
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name',)

class ClientConfigurationsViewSet(viewsets.ViewSet):    
    parser_classes = (CamelCaseJSONParser,)
    renderer_classes = (CamelCaseJSONRenderer,)
    authentication_classes=[CsrfExemptSessionAuthentication]
    
    @action(detail=False, methods=['GET'], permission_classes=[], )
    def teachers_obligation(self, request): 
        user = self.request.user
        
        return Response(
            {
                'initials': ClientTeacherObligationConfigurationSerializer(user.client_teacher_configuration(level=ClientTeacherObligationConfiguration.ELEMENTARY_SCHOOL)).data,
                'finals': ClientTeacherObligationConfigurationSerializer(user.client_teacher_configuration(level=ClientTeacherObligationConfiguration.ELEMENTARY_SCHOOL_2)).data,
                'high': ClientTeacherObligationConfigurationSerializer(user.client_teacher_configuration(level=ClientTeacherObligationConfiguration.HIGHT_SCHOOL)).data,
            }
        )
        
    @action(detail=False, methods=['POST', 'PATCH'])
    def create_update_teachers_obligation(self, request): 
        user = self.request.user
        client = user.client
        
        level = self.request.data.get('level')

        teacher_obligation, created = ClientTeacherObligationConfiguration.objects.using('default').get_or_create(client=client, level=level)
        
        if request.method == 'POST':
            serializer = ClientTeacherObligationConfigurationSerializer(instance=teacher_obligation, data=request.data)
        elif request.method == 'PATCH':
            serializer = ClientTeacherObligationConfigurationSerializer(instance=teacher_obligation, data=request.data, partial=True)
        
        serializer.is_valid(raise_exception=True)
        serializer.save(client=client)
        
        return Response(serializer.data)
