from django.urls import include, path, re_path
from django.views.generic import TemplateView

from .applications.views import ApplicationDetailView
from .auth.views import (
    TokenView, SocialView, RefreshTokenView, RevokeTokenView, LogoutView, AccountViewSet,
    UserStarterOnboardingViewSet, UserMoodViewSet,
    PasswordResetView, PasswordResetConfirmView,
)
from .school_classes.views import ColleagueListView
from .students.views import (
  StudentViewSet,
  ApplicationStudentViewSet
)

from rest_framework.routers import DefaultRouter

app_name = 'app'
router = DefaultRouter()
router.register(r'student', StudentViewSet, basename='student')
router.register(r'applications', ApplicationStudentViewSet, basename='applications')

app_name = 'app'

urlpatterns = [
    path('login/', TokenView.as_view(), name='token'),
    path('social/', SocialView.as_view(), name='social'),
    path('refresh/', RefreshTokenView.as_view(), name='refresh'),
    path('logout/', RevokeTokenView.as_view(), name='revoke'),
    path('django/logout/', LogoutView.as_view(), name='django-logout'),

    path('password/reset/', PasswordResetView.as_view(), name='password-reset'),
    path('password/reset/confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),

    path('user/', AccountViewSet.as_view(), name='user'),
    path('preferences/', UserStarterOnboardingViewSet.as_view(), name='update-preferences'),
    path('mood/', UserMoodViewSet.as_view(), name='update-mood'),
    path('colleagues/', ColleagueListView.as_view(), name='colleagues'),
    path('tmp/applications/<uuid:pk>/', ApplicationDetailView.as_view(), name='application-detail'),
] + router.urls
