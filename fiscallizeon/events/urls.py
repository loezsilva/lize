from django.urls import path

from fiscallizeon.events.api import events, text_message, application_message, question_error_report

app_name = 'events'

urlpatterns = [
	path('api/cadastrar', events.event_create, name='event_create'),
	path('api/<uuid:pk>/editar', events.event_update, name='event_update'),
	path('api/<uuid:pk>/finish', events.event_finish, name='event_finish'),
	path('api/mensagem/criar', text_message.text_message_create, name='text_message_create'),
	path('api/mensagem/aplicacao/criar', application_message.aplication_message_create, name='aplication_message_create'),
	path('api/erro-questao/novo', question_error_report.question_error_report_create, name='question_error_report_create'),
	# path('api/erro-questao/<uuid:pk>', question_error_report.question_error_report_retrieve, name='question_error_report_retrieve'),
]