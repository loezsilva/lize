from django.contrib.auth import views as auth_views
from django.urls import path
from rest_framework.routers import DefaultRouter

from fiscallizeon.accounts.views import password_change, verify_2fa, login_view, reset_password, reset_password_confirm, sso_login_view, SignUpView, CustomLogoutView

from .views import UserChangePermissions, GrupoPermissionsListView, GrupoPermissionsCreateUpdateView

app_name = 'accounts'


urlpatterns = [
	path('sso/', sso_login_view, name='sso_login'),
    path('entrar/', login_view, name='login'),
    path('cadastrar/', SignUpView.as_view(), name='signup'),
    path('sair/', CustomLogoutView.as_view(next_page='accounts:login'), name='logout'),
    path('verify_2fa/<uuid:user_id>/', verify_2fa, name='verify_2fa'),

    path(
        'alterar-senha/',
        password_change,
        name='password_change'
    ),
    path(
        'alterar-senha/concluido/',
        auth_views.PasswordChangeDoneView.as_view(),
        name='password_change_done'
    ),
    path('resetar-senha/', reset_password, name='password_reset'),
    path('confirmar-redefinicao/<uidb64>/<token>/',
        reset_password_confirm,
        name='password_reset_confirm'),
    path(
        'resetar-senha/solicitado/',
        auth_views.PasswordResetDoneView.as_view(template_name='accounts/password-reset/password_reset_done.html'),
        name='password_reset_done'
    ),
    path(
        'resetar-senha/concluido/',
        auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password-reset/password_reset_complete.html'),
        name='password_reset_complete'
    ),
    path('<uuid:pk>/permissoes/', UserChangePermissions.as_view(), name='user_permissions'),
    
    path('permissoes/', GrupoPermissionsListView.as_view(), name='groups'),
    path('permissoes/criar/', GrupoPermissionsCreateUpdateView.as_view(), name='groups_create'),
    path('permissoes/<uuid:pk>/', GrupoPermissionsCreateUpdateView.as_view(), name='groups_update'),
]