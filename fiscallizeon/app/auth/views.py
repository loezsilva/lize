import json

from django.contrib.auth import logout
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import View

from djangorestframework_camel_case.render import CamelCaseJSONRenderer
from dj_rest_auth.views import PasswordResetView as PasswordResetViewDjRestAuth, PasswordResetConfirmView as PasswordResetConfirmViewDjRestAuth
from drf_social_oauth2.oauth2_backends import KeepRequestCore
from drf_social_oauth2.oauth2_endpoints import SocialTokenServer
from oauth2_provider.models import get_access_token_model
from oauth2_provider.settings import oauth2_settings
from oauth2_provider.signals import app_authorized
from oauth2_provider.views import RevokeTokenView as RevokeTokenViewOAuth
from oauth2_provider.views.mixins import OAuthLibMixin
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from fiscallizeon.core.utils import CamelCaseAPIMixin
from fiscallizeon.accounts.models import User
from fiscallizeon.core.permissions import IsStudentUser, CanAccessApp

from .serializers import AccountSerializer, UserStarterOnboardingSerializer, UserMoodSerializer


def filter_dict_by_keys(dict, keys):
    return {key: value for key, value in dict.items() if key in keys}

class AuthView:
    renderer = CamelCaseJSONRenderer
    serializer_class = AccountSerializer

    def _render_data(self, data):
        return self.renderer().render(data).decode('utf-8')

    def _get_response(self, content, status, headers):
        response = HttpResponse(content=content, status=status)

        for k, v in headers.items():
            response[k] = v

        return response


@method_decorator(csrf_exempt, name='dispatch')
class TokenView(OAuthLibMixin, View, AuthView):
    @method_decorator(sensitive_post_parameters('password'))
    def post(self, request, *args, **kwargs):
        url, headers, body, status = self.create_token_response(request)
        if status == 200:
            dict_body = json.loads(body)
            access_token = dict_body.get('access_token')
            if access_token is not None:
                token = get_access_token_model().objects.using('default').get(token=access_token)
                app_authorized.send(sender=self, request=request, token=token)

                dict_body['expires_unix_epoch'] = int(token.expires.timestamp())

                serializer = self.serializer_class(token.user, context=dict_body)
                body = self._render_data(serializer.data)

        return self._get_response(body, status, headers)


@method_decorator(csrf_exempt, name='dispatch')
class SocialView(OAuthLibMixin, View, AuthView):
    server_class = SocialTokenServer
    validator_class = oauth2_settings.OAUTH2_VALIDATOR_CLASS
    oauthlib_backend_class = KeepRequestCore

    def post(self, request, *args, **kwargs):
        url, headers, body, status = self.create_token_response(request)
        if status == 200:
            dict_body = json.loads(body)
            access_token = dict_body.get('access_token')
            if access_token is not None:
                token = get_access_token_model().objects.using('default').get(token=access_token)
                app_authorized.send(sender=self, request=request, token=token)

                dict_body['expires_unix_epoch'] = int(token.expires.timestamp())

                serializer = self.serializer_class(token.user, context=dict_body)
                body = self._render_data(serializer.data)

        return self._get_response(body, status, headers)


@method_decorator(csrf_exempt, name='dispatch')
class RefreshTokenView(TokenView):
    pass


@method_decorator(csrf_exempt, name='dispatch')
class RevokeTokenView(RevokeTokenViewOAuth):
    pass


@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(APIView):
    http_method_names = ['post']
    required_scopes = ['read', 'write']

    def post(self, request):
        logout(request)
        return Response({'detail': 'Ok.'})


class PasswordResetView(CamelCaseAPIMixin, PasswordResetViewDjRestAuth):
    pass


class PasswordResetConfirmView(CamelCaseAPIMixin, PasswordResetConfirmViewDjRestAuth):
    pass

class AccountViewSet(CamelCaseAPIMixin, generics.RetrieveAPIView):
    serializer_class = AccountSerializer
    permission_classes = (permissions.IsAuthenticated, IsStudentUser, CanAccessApp)

    def get_object(self):
        return self.request.user

    def get_serializer_context(self):
        print('GET REFRESH USER DATA')
        context = super().get_serializer_context()
        context.update({
            'access_token': self.request.auth.token,
            'expires_in': oauth2_settings.ACCESS_TOKEN_EXPIRE_SECONDS,
            'expires_unix_epoch': int(self.request.auth.expires.timestamp()),
            'token_type': 'Bearer',
            'scope': self.request.auth.scope,
            'refresh_token': self.request.auth.refresh_token.token,
        })
        return context


class UserStarterOnboardingViewSet(CamelCaseAPIMixin, generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserStarterOnboardingSerializer
    permission_classes = (permissions.IsAuthenticated, IsStudentUser,)

    def patch(self, request, *args, **kwargs):
        serializer = self.serializer_class(request.user, data=request.data, partial=True)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        serializer.save()
        response = filter_dict_by_keys(serializer.data, request.data.keys())
        return Response(response)


class UserMoodViewSet(CamelCaseAPIMixin, generics.UpdateAPIView):
    serializer_class = UserMoodSerializer
    permission_classes = (permissions.IsAuthenticated, IsStudentUser,)

    def get_object(self):
        return self.request.user
