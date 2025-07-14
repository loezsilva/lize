from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from fiscallizeon.accounts.models import TwoFactorAuth
from django.utils import timezone

class VerifyTwoFactorCodeAPIView(APIView):
    required_permissions = [settings.TEACHER, settings.COORDINATION]

    def post(self, request):
        user = request.user
        code = request.data.get('code')
        
        two_factor_auth = TwoFactorAuth.objects.filter(user=user).first()

        if not two_factor_auth:
            return Response({'error': 'Autenticação de dois fatores não configurada.'}, status=status.HTTP_400_BAD_REQUEST)

        if two_factor_auth.two_factor_code == code and timezone.now() <= two_factor_auth.expire_in:
            two_factor_auth.is_verified = True
            two_factor_auth.save()
            user.two_factor_enabled = not user.two_factor_enabled
            user.save()

            return Response({
                'message': 'Código de autenticação verificado com sucesso. Autenticação de dois fatores ativada.',
                'two_factor_enabled': user.two_factor_enabled
            }, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Código inválido ou expirado.'}, status=status.HTTP_400_BAD_REQUEST)
        
class SendTwoFactorCodeAPIView(APIView):
    required_permissions = [settings.TEACHER, settings.COORDINATION]

    def post(self, request):
        user = request.user
        two_factor_auth, created = TwoFactorAuth.objects.get_or_create(user=user)
        two_factor_auth.generate_code()
        two_factor_auth.send_code_email()

        return Response({
            'message': 'Código de autenticação enviado com sucesso.',
        }, status=status.HTTP_200_OK)