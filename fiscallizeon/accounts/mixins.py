from rest_framework.authtoken.models import Token

from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth import login


class LoginOrTokenRequiredMixin(UserPassesTestMixin):

    def test_func(self):
        if self.request.user.is_authenticated:
            return True

        auth_header = self.request.META.get('HTTP_TOKENAUTH', '').split()

        if len(auth_header) != 2:
            return False

        try:
            request_type = auth_header[0]
            request_token = auth_header[1]
            token = Token.objects.filter(key=request_token).first()

            if request_type != 'Token' or not token:
                return False

            if request_token == token.key:
                login(self.request, token.user, backend='django.contrib.auth.backends.ModelBackend')
                return True
        except IndexError:
            return False
