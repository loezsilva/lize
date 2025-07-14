from django.conf import settings 
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from rest_framework.generics import CreateAPIView, ListAPIView, DestroyAPIView
from rest_framework.views import APIView
from fiscallizeon.clients.models import CoordinationMember, SchoolCoordination
from fiscallizeon.accounts.models import User
from rest_framework.filters import SearchFilter
from django.core.cache import cache

from fiscallizeon.clients.serializers2.coordination_member import (
    CoordinationMemberUserSerializer,
    CoordinationMemberUserCreateSerializer,
)
from fiscallizeon.core.api.csrf_exempt_session import CsrfExemptSessionAuthentication

from fiscallizeon.inspectors.models import Inspector
from fiscallizeon.core.paginations import LimitOffsetPagination

@extend_schema(tags=['Coordenações (Membros)'])
class UserCoordinationMemberListAPIView(ListAPIView):
    serializer_class = CoordinationMemberUserSerializer
    queryset = User.objects.filter(is_active=True)
    pagination_class = LimitOffsetPagination
    filter_backends = [SearchFilter]
    search_fields = ['name', 'email']
    required_scopes = ['read', 'write']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(coordination_member__coordination__in=self.request.user.get_coordinations_cache())
        return queryset.distinct()
    
@extend_schema(tags=['Coordenações (Membros)'])
class UserCoordinationMemberCreateAPIView(CreateAPIView):
    serializer_class = CoordinationMemberUserCreateSerializer
    required_scopes = ['read', 'write']
    
    def create(self, request, *args, **kwargs):
        user = self.request.user
        data = request.data
        
        user_data = data
        
        user_instance, created = User.objects.update_or_create(
            email=user_data.get('email'),
            defaults={
                "username": user_data.get('email'),
                "must_change_password": False,
                "is_active": True,
            }
        )
        
        if created:
            user_instance.must_change_password = True
            user_instance.save()

        if user_data.get('name'):
            user_instance.name = user_data.get('name')
        
        user_instance.set_password(user_instance.email)
        user_instance.save()
        
        for coordination_object in data.get("coordination_member").copy():
            if not coordination_object.get('coordination') in user.get_coordinations_cache(): 
                Response('O usuário não pertence a esta coordenação', status=status.HTTP_400_BAD_REQUEST)

            member, member_created = CoordinationMember.objects.update_or_create(
                coordination=SchoolCoordination.objects.get(pk=coordination_object.get('coordination')),
                user=user_instance,
                defaults={
                    "is_pedagogic_reviewer": coordination_object.get('is_pedagogic_reviewer') or False,
                    "is_coordinator": coordination_object.get('is_coordinator') or False,
                    "is_reviewer": coordination_object.get('is_reviewer') or False
                }
            )
            
        # Adiciona grupos padrão ao criar um membro
        if data.get('permission_groups'):
            user_instance.custom_groups.set(data.get('permission_groups'))
            
        else:
            # Se o cliente tiver algum grupo padrão eu seto esses grupos
            # se não eu pego os grupos padrões da Lize
            if user_instance.client.has_default_groups('coordination'):
                user_instance.custom_groups.set(user_instance.client.get_groups().filter(
                    client__isnull=False, segment='coordination', default=True
                ))
            else:
                user_instance.custom_groups.set(user_instance.client.get_groups().filter(
                    client__isnull=True, segment='coordination', default=True
                ))
        
        # if not created:
        #     inspector = Inspector.objects.filter(
        #         user=user_instance
        #     )

        #     if inspector:
        #         inspector.user = None
        #         inspector.save()

        headers = self.get_success_headers(CoordinationMemberUserSerializer(instance=user_instance))
        
        return Response(CoordinationMemberUserSerializer(instance=user_instance).data, status=status.HTTP_201_CREATED, headers=headers)
    
@extend_schema(tags=['Coordenações (Membros)'])
class UserCoordinationMemberDisableAPIView(APIView):
    # authentication_classes = (CsrfExemptSessionAuthentication, )
    required_scopes = ["read", "write"]

    @extend_schema(request=None, responses=[])
    def post(self, request, pk):
        
        try:
            user = self.request.user
            user_to_disable = User.objects.get(pk=pk)
            
            if user.client == user_to_disable.client:

                coordinations_member = user_to_disable.coordination_member.all()
                
                if coordinations_member:
                    # Verifica se o coordenador tem algum professor associado
                    # Caso tenha, não podemos desativar o usuário do coordenador
                    # Pois ele perderá o acesso com o professor
                    # O correto a fazer é Remover o CoordinationMember e deixar o usuário ativo 
                    if hasattr(user_to_disable, 'inspector') and user_to_disable.inspector:
                        CACHE_KEY = f'USER_TYPE_{user_to_disable.id}'
                        cache.set(CACHE_KEY, settings.TEACHER)

                        # Essa parte remove os grupos de coordenadores desse usuário
                        coordination_groups = user_to_disable.custom_groups.filter(segment=settings.COORDINATION)
                        user_to_disable.custom_groups.remove(*coordination_groups)
                        coordinations_member.delete()
                    else:
                        user_to_disable.is_active = False
                        user_to_disable.save()
                    
                    return Response("Membro da coordenação desativado com sucesso.")
        
        except User.DoesNotExist:
            pass

        return Response("Membro da coordenação não encontrado.", status=status.HTTP_404_NOT_FOUND)
    
@extend_schema(tags=['Coordenações (Membros)'])
class UserCoordinationMemberActivateAPIView(APIView):
    # authentication_classes = (CsrfExemptSessionAuthentication, )
    required_scopes = ["read", "write"]

    @extend_schema(request=None, responses=[])
    def post(self, request, pk):
        
        try:
            user = self.request.user
            user_to_active = User.objects.get(pk=pk)
            
            if user.client == user_to_active.client:
                user_to_active.is_active = True
                user_to_active.save()
                return Response("Membro da coordenação ativado com sucesso.")
        
        except User.DoesNotExist:
            pass

        return Response("Membro da coordenação não encontrado.", status=status.HTTP_404_NOT_FOUND)
    
@extend_schema(tags=['Coordenações (Membros)'])
class CoordinatiomMemberDestroyAPIView(DestroyAPIView):
    queryset = CoordinationMember.objects.all()
    required_scopes = ['read', 'write']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(coordination__in=self.request.user.get_coordinations_cache())
        return queryset
    

class CheckInspectorAssociationAPI(APIView):
    def get(self, request, *args, **kwargs):
        email = request.query_params.get("email")

        if not email:
            return Response(
                {"error": "E-mail não fornecido"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        email_exists = Inspector.objects.filter(email=email).exists()
        
        return Response({"email_exists": email_exists}, status=status.HTTP_200_OK)