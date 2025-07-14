from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from fiscallizeon.core.utils import CheckHasPermissionAPI
from fiscallizeon.accounts.models import User
from django.core.cache import cache
from django.conf import settings

class UserCoordinationMemberDisableAPIView(CheckHasPermissionAPI, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )

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
    
class UserCoordinationMemberActiveAPIView(CheckHasPermissionAPI, APIView):
    authentication_classes = (CsrfExemptSessionAuthentication, )

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