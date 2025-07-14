import json
import requests

from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, resolve_url as r
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash, login
from django.contrib.auth import views as auth_views
from django.contrib.sessions.models import Session
from django.http import HttpRequest
from django.urls import reverse_lazy
from django.utils import timezone
from fiscallizeon.accounts.models import  SSOTokenUser, User, CustomGroup, TwoFactorAuth
from fiscallizeon.accounts.serializers.sso import SSOLoginTokenSerializer
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import CreateView
from fiscallizeon.accounts.forms import UserCreationForm
from django.views.generic import TemplateView, DetailView, ListView
from fiscallizeon.core.utils import CheckHasPermission
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt

from oauth2_provider.models import AccessToken, Application, get_access_token_model, RefreshToken
from oauth2_provider.signals import app_authorized
from oauth2_provider.views.mixins import OAuthLibMixin

from social_core.actions import do_complete
from social_django.utils import psa
from social_django.views import NAMESPACE, _do_login


class GroupQuerySetMixin(object):
    queryset = CustomGroup.objects.all()
    
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(client=self.request.user.get_clients_cache()[0])
        return queryset

class UserChangePermissions(LoginRequiredMixin, CheckHasPermission, DetailView):
    permission_required = 'accounts.can_change_permissions'
    template_name = 'accounts/user_permissions.html'
    queryset = User.objects.all()
    context_object_name = 'my_user'

    def dispatch(self, request, *args, **kwargs):
        member = self.get_object()
        if member == request.user:
            messages.error(request, "Você não pode alterar suas próprias permissões.")
            return redirect(reverse_lazy('clients:members_list'))
        return super().dispatch(request, *args, **kwargs)

class GrupoPermissionsListView(LoginRequiredMixin, CheckHasPermission, GroupQuerySetMixin, ListView):
    permission_required = 'accounts.can_change_permissions'
    template_name = 'accounts/groups_list.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q_name"] = self.request.GET.get('q_name')
        context["q_segment"] = self.request.GET.getlist('q_segment')
        context["q_default"] = self.request.GET.get('q_default')
        
        return context
    
class GrupoPermissionsCreateUpdateView(LoginRequiredMixin, CheckHasPermission, TemplateView):
    permission_required = 'accounts.can_change_permissions'
    template_name = 'accounts/groups_create_update.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.kwargs.get('pk'):
            context["object"] = CustomGroup.objects.get(pk=self.kwargs['pk'], client__in=self.request.user.get_clients_cache())
        return context


def get_token_authorization(url, token, backend):
    response = requests.post(
        url,
        json={
            'grant_type': 'convert_token',
            'token': token,
            'backend': backend,
            'client_id': settings.CLIENT_ID_PRIVATE,
            'client_secret': settings.CLIENT_SECRET_PRIVATE,
        },
    )
    data = response.json()
    token = get_access_token_model().objects.using('default').get(token=data['accessToken'])
    return token


def set_cookie_authorization(response, token, session):
    response.set_cookie(
        key='authorization',
        value=quote(f'Bearer {token.token}'),
        domain=settings.FRONTEND_SHARED_DOMAIN, # '.localhost', # domain
        httponly=True,
        secure=False if settings.DEBUG else True,
        expires=token.expires,
        samesite='Lax',
        path='/',
    )
    response.set_cookie(
        key='sessionidref',
        value=session.session_key,
        domain=settings.FRONTEND_SHARED_DOMAIN,
        httponly=True,
        secure=False if settings.DEBUG else True,
        samesite='Lax',
        path='/',
    )


def get_lastest_refresh_token(user):
    refresh_token = RefreshToken.objects.using('default').filter(user=user).order_by('created').last()
    return refresh_token


def refresh_token(request, refresh_token_value):
    request_url = request.build_absolute_uri(r('app:token'))
    url = request_url.replace('http:', 'https:')
    response = requests.post(
        url,
        json={
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token_value,
            'client_id': settings.CLIENT_ID_PRIVATE,
            'client_secret': settings.CLIENT_SECRET_PRIVATE,
        },
    )
    data = response.json()
    token = get_access_token_model().objects.using('default').get(token=data['accessToken'])
    return token


class LoginView(auth_views.LoginView, OAuthLibMixin):
    # template_name='accounts/login.html'
    template_name='redesign/login.html'
    redirect_authenticated_user=True

    def get_template_names(self):
        if 'amentorizze.com.br' in self.request.META.get('HTTP_HOST'):

            return 'accounts/login_mentorizze.html'
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["email"] = self.request.GET.get('email')
        return context

    def _get_oauth_request(self, form_cleaned_data):
        data = {
            'grant_type': 'password',
            'username': form_cleaned_data['username'],
            'password': form_cleaned_data['password'],
            'client_id': settings.CLIENT_ID_PRIVATE,
            'client_secret': settings.CLIENT_SECRET_PRIVATE,
        }
        oauth_request = HttpRequest()
        oauth_request.method = 'POST'
        oauth_request.path = r('app:token')
        oauth_request.content_type = 'application/json'
        oauth_request._body = json.dumps(data).encode('utf-8')
        oauth_request.META['CONTENT_TYPE'] = 'application/json'
        return oauth_request

    def form_valid(self, form):
        user = form.get_user()
        response = super().form_valid(form)
        print("ENTOU AQUI MSMO LOGANDO COM O GOOGLE")
        if user.is_authenticated and hasattr(user, 'student') and user.client_can_access_app:
            oauth_request = self._get_oauth_request(form.cleaned_data)
            url, headers, body, status = self.create_token_response(oauth_request)
            if status == 200:
                access_token = json.loads(body).get('access_token')
                if access_token is not None:
                    token = get_access_token_model().objects.using('default').get(token=access_token)
                    app_authorized.send(sender=self, request=oauth_request, token=token)
                    set_cookie_authorization(response, token, self.request.session)
        
        client = user.client
        if user and client:
            if session_timeout_minutes := user.client_session_timeout_minutes:
                if hasattr(self.request, 'session'):
                    expire_time = session_timeout_minutes * 60
                    self.request.session.set_expiry(expire_time)
            
            if (user.user_type == "teacher" or user.user_type == "coordination") and (user.two_factor_enabled or client.two_factor_enabled):
                two_factor_auth, created = TwoFactorAuth.objects.get_or_create(user=user)
                two_factor_auth.generate_code()
                two_factor_auth.send_code_email()
                return redirect(reverse_lazy('accounts:verify_2fa', kwargs={'user_id': user.id}))
        return response

login_view = LoginView.as_view()

def verify_2fa(request, user_id):
    if request.method == 'POST':
        code = request.POST.get('code')
        two_factor_auth = TwoFactorAuth.objects.filter(user_id=user_id).first()

        if two_factor_auth and two_factor_auth.two_factor_code == code and timezone.now() <= two_factor_auth.expire_in:
            two_factor_auth.is_verified = True
            two_factor_auth.save()
            user = User.objects.filter(id=user_id).first()
            login(request, user,  backend='fiscallizeon.core.auth_backends.EmailOrUsernameModelBackend')

            return redirect('core:redirect_dashboard')

        error_message = "Código inválido ou expirado."
        return render(request, 'accounts/verify_2fa.html', {'user_id': user_id, 'error_message': error_message})

    return render(request, 'accounts/verify_2fa.html', {'user_id': user_id})


@login_required
def password_change(request):
    template_name = 'accounts/password_change.html'
    context = {}
    
    form = PasswordChangeForm(data=request.POST or None, user=request.user)
    if form.is_valid():
        form.save()
        messages.info(request, 'Senha alterada com sucesso!')
        update_session_auth_hash(request, form.user)
        request.session['must_change_password'] = False
        request.user.must_change_password = False
        request.user.save()
        return redirect('core:redirect_dashboard')
    
    context['must_change_password'] = request.session.get('must_change_password', False)
    context['hide_navbar'] = request.session.get('must_change_password', False)
    context['form'] = form
    return render(request, template_name, context)

class ResetPassword(auth_views.PasswordResetView):
    template_name = 'accounts/password-reset/password_reset.html'
    html_email_template_name = 'accounts/password-reset/password_reset_email.html'
    email_template_name = 'accounts/password-reset/password_reset_email.html'
    subject_template_name = 'accounts/password-reset/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')

reset_password = ResetPassword.as_view()

class ResetPasswordConfirm(auth_views.PasswordResetConfirmView):
    template_name = 'accounts/password-reset/password_reset_confirm.html'
    success_url = reverse_lazy('core:redirect_dashboard')


def sso_login_view(request):
    access_token = request.GET.get('access_token', None)
    access_token_serializer = SSOLoginTokenSerializer(data={'access_token':access_token})

    if access_token_serializer.is_valid():
        valid_token = SSOTokenUser.objects.filter(
            access_token=access_token_serializer.data.get('access_token'),
            expire_in__gt=timezone.localtime(timezone.now())
        ).first()

        if valid_token:
            valid_token.user.must_change_password =  False
            valid_token.user.save()
            login(request, valid_token.user, backend='fiscallizeon.core.auth_backends.EmailOrUsernameModelBackend')
            return redirect("core:redirect_dashboard")
        
        messages.error(request, "Token de acesso fornecido inválido ou expirou!")
        return redirect("accounts:logout")
    
    messages.error(request, "Token de acesso não fornecido ou inválido!")
    return redirect("accounts:logout")

reset_password_confirm = ResetPasswordConfirm.as_view()

class SignUpView(SuccessMessageMixin, CreateView):
    form_class = UserCreationForm
    success_url = reverse_lazy('core:redirect_dashboard')
    template_name = 'redesign/registration.html'
    success_message = 'Seu cadastro foi realizado com sucesso.'

    def get_success_url(self):
    
        user = self.object
        
        user.create_teacher()

        user.is_freemium = True

        user.save()

        login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')

        return super().get_success_url()


class CustomLogoutView(auth_views.LogoutView):
    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        session_id_ref = request.COOKIES.get('sessionidref')
        if session_id_ref:
            Session.objects.filter(session_key=session_id_ref).delete()
            response.delete_cookie('sessionidref')
        return response


@never_cache
@csrf_exempt
@psa(f'{NAMESPACE}:complete')
def custom_social_auth_complete(request, backend, *args, **kwargs):
    response = do_complete(
        request.backend,
        _do_login,
        user=request.user,
        redirect_name=REDIRECT_FIELD_NAME,
        request=request,
        *args,
        **kwargs,
    )
    user = request.user
    if user.is_authenticated and hasattr(user, 'student') and user.client_can_access_app:
        url = request.build_absolute_uri(r('app:social'))
        access_token = user.social_user.extra_data.get('access_token')
        token = get_token_authorization(url.replace('http:', 'https:'), access_token, backend)
        set_cookie_authorization(response, token, request.session)

    return response
