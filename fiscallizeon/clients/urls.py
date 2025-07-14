from django.urls import path

from fiscallizeon.clients.admin import admin_hijack_client
from fiscallizeon.clients.views import members
from fiscallizeon.clients.views import clients
from fiscallizeon.clients.api.membros import (
    UserCoordinationMemberDisableAPIView,
    UserCoordinationMemberActiveAPIView,
)

app_name = 'clients'

urlpatterns = [
    path('', members.members_list, name='members_list'),
	path('cadastrar/', members.members_create, name='members_create'),
    path('<uuid:pk>/editar/', members.members_update, name='members_update'),
	path('<uuid:pk>/remover/', members.members_delete, name='members_delete'),
	path('<uuid:pk>/reset/', members.members_password_reset, name='members_password_reset'),
	path('configuracao/', clients.ConfigurationRedirectView.as_view(), name='configurations'),
	path('obrigatoriedade/professor/', members.obligation_teacher_configuration, name='obligation_teacher_configuration'),
	path('questoes/configuracoes/', members.QuestionsConfigurationsTemplateView.as_view(), name='questions_configurations'),
	path('configuracao/malotes/<uuid:pk>/', members.ConfigOMRConfigurationUpdateView.as_view(), name='update_client_omr_configuration'),
	path('exportar/', members.members_export, name='export_members_csv'),
 
	# Notificações
    path('configuracao/notificacoes/', members.ConfigNotificationsCreateView.as_view(), name='config_notifications_create'),
    path('configuracao/notificacoes/<uuid:pk>/', members.ConfigNotificationsUpdateView.as_view(), name='config_notifications_update'),

	# Tags de questões
	path('configuracao/tags/', members.QuestionTagListView.as_view(), name='question_tag_list'),
	path('configuracao/tags/criar', members.QuestionTagCreateView.as_view(), name='question_tag_create'),
    path('configuracao/tags/<uuid:pk>/editar/', members.QuestionTagUpdateView.as_view(), name='question_tag_update'),
    path('configuracao/tags/<uuid:pk>/remover/', members.QuestionTagDeleteView.as_view(), name='question_tag_delete'),
    
	# Padrão de impressão
	path('padrao/configuracao/', clients.ExamPrintConfigsListTemplateView.as_view(), name='print-configs-list'),
	path('padrao/configuracao/cadastrar/', clients.ExamPrintConfigsCreateTemplateView.as_view(), name='print-configs-create'),
	path('padrao/configuracao/atualizar/<uuid:pk>/', clients.ExamPrintConfigsUpdateTemplateView.as_view(), name='print-configs-update'),

	# Parceiros
	path('parceiros', clients.PartnersListView.as_view(), name='partners_list'),
	path('parceiros/cadastrar', clients.PartnerCreateView.as_view(), name='partners_create'),
	path('parceiros/editar/<uuid:pk>/', clients.PartnerUpdateView.as_view(), name='partner_update'),
	path('parceiros/deletar/<uuid:pk>/', clients.PartnerDeleteView.as_view(), name='partner_delete'),

	# Etapa de ensino
	path('etapa/ensino/configuracao/', clients.TeachingStageListTemplateView.as_view(), name='teaching-stage-list'),
	path('etapa/ensino/configuracao/cadastrar/', clients.TeachingStageCreateTemplateView.as_view(), name='teaching-stage-create'),
	path('etapa/ensino/configuracao/atualizar/<uuid:pk>/', clients.TeachingStageUpdateTemplateView.as_view(), name='teaching-stage-update'),

	# Sistema de ensino
	path('sistema/ensino/configuracao/', clients.EducationSystemListTemplateView.as_view(), name='education-system-list'),
	path('sistema/ensino/configuracao/cadastrar/', clients.EducationSystemCreateTemplateView.as_view(), name='education-system-create'),
	path('sistema/ensino/configuracao/atualizar/<uuid:pk>/', clients.EducationSystemUpdateTemplateView.as_view(), name='education-system-update'),

	path("hijack/acquire/<uuid:pk>/", admin_hijack_client, name="admin-hijack-client"),
    
	# API
    path("desativar/<uuid:pk>/", UserCoordinationMemberDisableAPIView.as_view(), name='disable-coordination-member'),
    path("ativar/<uuid:pk>/", UserCoordinationMemberActiveAPIView.as_view(), name='active-coordination-member'),
]