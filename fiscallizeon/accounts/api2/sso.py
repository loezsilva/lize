import uuid
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from ..models import User, SSOTokenUser
from fiscallizeon.core.api import CsrfExemptSessionAuthentication
from rest_framework.authentication import TokenAuthentication
from drf_spectacular.utils import extend_schema

from fiscallizeon.core.utils import CheckHasPermissionAPI
from django.conf import settings
from rest_framework import status
from django.utils import timezone
from datetime import timedelta

from fiscallizeon.accounts.serializers.sso import SSOGenerateAcessTokenSerializer, SSOGenerateAcessTokenResponseSerializer

@extend_schema(tags=['Autenticação SSO'])
class SSOViewSet(viewsets.GenericViewSet):
    required_permissions = [settings.COORDINATION]
    permission_classes = [CheckHasPermissionAPI]
    authentication_classes = [CsrfExemptSessionAuthentication, TokenAuthentication]
    
    @extend_schema(
        description="Para autenticar o usuário após adquirir o 'access_token', você deve direcioná-lo para \
        <a href='https://app.lizeedu.com.br/conta/sso/?access_token={access_token}'>https://app.lizeedu.com.br/conta/sso/?access_token={access_token}</a>",
        request=SSOGenerateAcessTokenSerializer,
        responses={
            200: SSOGenerateAcessTokenResponseSerializer
        }
    )
    @action(detail=False, methods=['POST'], serializer_class=SSOGenerateAcessTokenSerializer)
    def generate_accesss_token(self, request, pk=None):
        print(request.data, self.request.data)
        get_serializer = SSOGenerateAcessTokenSerializer(data=request.data)
        if get_serializer.is_valid():
            user = User.objects.get(email=get_serializer.data.get('email'), is_active=True)
            user_client = user.get_clients().first()
            request_user_client = request.user.get_clients().first()

            if not user:
                return Response("Usuário não encontrado.", status=status.HTTP_404_NOT_FOUND)

            if not user_client == request_user_client:
                return Response("Não autorizado.", status=status.HTTP_403_FORBIDDEN)
            
            token = SSOTokenUser.objects.filter(
                user=user
            ).first()

            if not token:
                token = SSOTokenUser.objects.create(
                    user=user,
                    expire_in=timezone.localtime(timezone.now())+timedelta(hours=1)
                )

            elif token.expire_in < timezone.localtime(timezone.now()):
                token.access_token = uuid.uuid4()
                token.refresh_token = uuid.uuid4()
                token.expire_in = timezone.localtime(timezone.now())+timedelta(hours=1)
                token.save(skip_hooks=True)

            return Response(SSOGenerateAcessTokenResponseSerializer(token).data, status=status.HTTP_200_OK)
        return Response(get_serializer.errors, status=status.HTTP_400_BAD_REQUEST)