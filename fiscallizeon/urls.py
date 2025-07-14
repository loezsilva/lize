"""fiscallizeon URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from drf_spectacular.views import (
    SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView,
)

from django.contrib import admin
from django.conf import settings
from django.http import HttpResponse
from django.urls import path, include, re_path
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from fiscallizeon.core.views import status, terms
from fiscallizeon.answers.views import AttachmentTemplateView, FileAnswerTemplateView

from fiscallizeon.applications.views import external_result_application
from fiscallizeon.accounts.views import login_view, custom_social_auth_complete
from django.views.static import serve

from fiscallizeon.candidates.views import subscribe_class
from fiscallizeon.core import http_error_handler
from fiscallizeon.core.views import analytics_coordination, analytics_detail_coordination
from fiscallizeon.ai.views import TextualDemoView

from social_core.utils import setting_name


extra = getattr(settings, setting_name('TRAILING_SLASH'), True) and '/' or ''

handler400 = http_error_handler.bad_request
handler403 = http_error_handler.permission_denied
handler404 = http_error_handler.page_not_found
handler500 = http_error_handler.server_error

def service_worker_onesignal(request):
    response = HttpResponse(open(settings.ONESIGNAL_SERVICE_WORKER_PATH).read(), content_type='application/javascript')
    return response

urlpatterns = [

    # path('', include('pwa.urls')),
    path('',  login_view, name='login'),
    path(settings.ADMIN_URL, admin.site.urls),
    path('conta/', include('fiscallizeon.accounts.urls', namespace='accounts')),
    path('diagramacoes/', include('fiscallizeon.diagramations.urls', namespace='diagramations')),
    path('painel/', include('fiscallizeon.core.urls', namespace='core')),
    path('turmas/', include('fiscallizeon.classes.urls', namespace='classes')),
    path('aplicacoes/', include('fiscallizeon.applications.urls', namespace='applications')),
    path('fiscais/', include('fiscallizeon.inspectors.urls', namespace='inspectors')),
    path('alunos/', include('fiscallizeon.students.urls', namespace='students')),
    path('eventos/', include('fiscallizeon.events.urls', namespace='events')),
    path('provas/', include('fiscallizeon.exams.urls', namespace='exams')),
    path('candidatos/', include('fiscallizeon.candidates.urls', namespace='candidates')),
    path('disciplinas/', include('fiscallizeon.subjects.urls', namespace='subjects')),
    path('bncc/', include('fiscallizeon.bncc.urls', namespace='bncc')),
    path('membros/', include('fiscallizeon.clients.urls', namespace='clients')),
    path('gabaritos/', include('fiscallizeon.omr.urls', namespace='omr')),
    path('gabaritos/nps/', include('fiscallizeon.omrnps.urls', namespace='omrnps')),
    path('exportacao/', include('fiscallizeon.exports.urls', namespace='exports')),
    path('ensalamento/', include('fiscallizeon.distribution.urls', namespace='distribution')),
    path('materiais/', include('fiscallizeon.materials.urls', namespace='materials')),
    path('integracoes/', include('fiscallizeon.integrations.urls', namespace='integrations')),
    path('correcoes/', include('fiscallizeon.corrections.urls', namespace='corrections')),
    path('painel/analitico/', include('fiscallizeon.analytics.urls', namespace='analytics')),
    path('questoes/', include('fiscallizeon.questions.urls', namespace='questions')),
    path('respostas/', include('fiscallizeon.answers.urls', namespace='answers')),
    path('responsaveis/', include('fiscallizeon.parents.urls', namespace='parents')),
    path('notificacoes/', include('fiscallizeon.notifications.urls', namespace='notifications')),
    path('ajuda/', include('fiscallizeon.help.urls', namespace='help')),
    path('onboarding/', include('fiscallizeon.onboarding.urls')),
    path('dashboards/', include('fiscallizeon.dashboards.urls', namespace='dashboards')),
    path('tinymce/', include('tinymce.urls')),
    path('status/', status, name="status"),
    path('demo-textual/', TextualDemoView.as_view(), name="textual-demo"),

	path('termos/<str:slug>/', terms, name='terms'),
	path('inscricao/<str:slug>/', subscribe_class, name='subscribe-class'),

    
    path('anexar/<uuid:exam_teacher_subject>/<uuid:application_student>/', AttachmentTemplateView.as_view(), name='qrcode-response-attachment'), 
    path('anexar/<uuid:question_id>/<uuid:application_student_pk>/<int:number>/', FileAnswerTemplateView.as_view(), name='qrcode-response'), 
    path('resultado-avaliacao/<uuid:pk>', external_result_application, name='external_result_application'),	

    path('analytics/', analytics_coordination, name='analytics-coordination'),
    path('analytics/detail/', analytics_detail_coordination, name='analytics-detail-coordination'),

    path('api/v1/', include('fiscallizeon.api.urls', namespace='api')),
    path('api/v2/', include('fiscallizeon.api2.urls', namespace='api2')),
    
    path('OneSignalSDKWorker.js', service_worker_onesignal),

    path(f'social-auth/complete/<str:backend>{extra}', custom_social_auth_complete, name='social-auth-complete'),

    path('social-auth/', include('social_django.urls', namespace='social-auth')),
    path('api/v3/api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api/v3/oauth/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    path('api/v3/auth/', include('drf_social_oauth2.urls', namespace='drf')),
    path('api/v3/', include('fiscallizeon.app.urls', namespace='app')),
    path('hijack/', include('hijack.urls')),
    path('sitemap.xml', serve, {'document_root': settings.STATICFILES_DIRS[0], 'path': 'app_lize_map.xml'}),
]

urlpatterns.extend([
    path('docs/download/', SpectacularAPIView.as_view(), name='schema'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'),name='redoc'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
])

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # urlpatterns.append(path('__debug__/', include('debug_toolbar.urls')))

    schema_view = get_schema_view(
    openapi.Info(
        title="Fiscallize API",
        default_version='v2',
        description="Test description",
        contact=openapi.Contact(email="contato@fiscallize.com.br"),
        ),
        public=True,
    )

    urlpatterns.extend([
        re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
        path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
        path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    ])