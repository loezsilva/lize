from django.db.models import Q
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.backends import ModelBackend

class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        
        try:
            user = User.objects.get(Q(username=username)|Q(email=username))
            if user.client_has_allow_login_only_google and not user.is_staff and not user.user_type == settings.PARENT:
                messages.warning(request, "Sua instituição permite login apenas com o Google.")
                return None
            if user.check_password(password) and self.user_can_authenticate(user):
                if hasattr(request, 'session'):
                    expire_time = (user.client_session_timeout_minutes or 0) * 60
                    request.session.set_expiry(expire_time or 0)
                return user
        except User.DoesNotExist:
            User().set_password(password)
        except User.MultipleObjectsReturned:
            return None
        except Exception as e:
            return None