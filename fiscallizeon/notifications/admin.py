from .forms import NotificationForm
from import_export.admin import ImportExportModelAdmin
from .models import Notification, NotificationUser
from fiscallizeon.clients.models import Client
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.db.models import Q
from fiscallizeon.notifications.models import Notification
from import_export import resources, fields, widgets
from import_export.admin import ExportMixin
from import_export.fields import Field

# Register your models here.

class ClientFilter(SimpleListFilter):
	title = 'Cliente'
	parameter_name = 'client'

	def lookups(self, request, model_admin):
		query = Client.objects.all()
		return [ (item.pk, item.name) for item in query ]

	def queryset(self, request, queryset):
		if not self.value():
			return queryset
		else:
			client = Client.objects.get(pk=self.value())
			return queryset.filter(
				Q(clients=client)
			).distinct()
		
		return

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
	list_display = ('title', 'start_date', 'feedbacks', 'end_date', 'get_target_clients', 'is_finished')
	list_filter = ('category', ClientFilter)
	search_fields = ('title', 'description')
	autocomplete_fields = ("users", "viewed_by")
	form = NotificationForm
	fieldsets = (
		("Configurações da notificação", {
			"fields": (
				'category',
				'title',
				'description',
				'content',
				'repeat_days',
			)
		}),
		("Período da notificação", {
			"fields": (
				'start_date',
				'end_date',
			)
		}),
		("Configurações da modal", {
			"fields": (
				'modal_height',
				'modal_width',
			)
		}),
		("Público alvo", {
			"fields": (
				'clients',
				'users', 
				'segments',
				'high_school',
				'elementary_school',
			)
		}),
		("Configurações da notificação", {
			"fields": (
				"type",
				"nps_type",
				"show_modal",
				"delay",
				"show_rating",
				"show_form",
			),
		}),
		("Chamar modal em ações específicas", {
			"fields": (
				"urls",
				"trigger",
				"model",
				"especial_trigger",
			),
		}),
	)
	

	def feedbacks(self, obj):
		return obj.notificationuser_set.filter(feedback__isnull=False).count()

class NotificationUserResource(resources.ModelResource):
	notification = Field('notification', 'Notificação')

	next_nps_date = fields.Field(
		attribute="next_nps_date",
		column_name="Próxima pesquisa",
		widget=widgets.DateWidget(format="%d/%m/%Y")
	)
	
	usuario = fields.Field(attribute='user', column_name="Usuário")
	
	user_id = fields.Field(
		attribute="user__id",
		column_name="ID do usuário",
	)

	client_name = fields.Field(
		column_name="Nome do cliente",
	)

	def dehydrate_client_name(self, obj):
		client = obj.user.client
		return client.name if client else '-'

	user_type = fields.Field(
		column_name="Tipo de usuário"
	)

	def dehydrate_user_type(self, obj):
		return obj.user.user_type_display()
	
	rating = fields.Field(
		attribute="rating",
		column_name="Nota",
	)
	
	feedback_sent = fields.Field(
		attribute="feedback_sent",
		column_name="Foi enviado",
	)

	type = fields.Field(
		attribute="notification__get_type_display",
		column_name="Tipo",
	)

	viewed = fields.Field(
		'viewed',
		'Visualizado'
	)

	class Meta:
		model = NotificationUser
		fields = ['next_nps_date', 'type', 'rating', 'feedback_sent', 'user_id', 'usuario', 'user_type', 'client_name', 'feedback', 'viewed']
		report_skipped = False
		using_db = 'readonly2'
	
	def dehydrate_viewed(self, notification_user):
		return 'Sim' if notification_user.viewed else 'Não'

	def dehydrate_feedback_sent(self, notification_user):
		return 'Sim' if notification_user.feedback_sent else 'Não'

class NotificationUserClientFilter(ClientFilter):
	def queryset(self, request, queryset):
		if not self.value():
			return queryset
		else:
			client = Client.objects.get(pk=self.value())
			for feedback in queryset:
				if feedback.user.get_clients_cache()[0] != client.pk:
					queryset = queryset.exclude(pk=feedback.pk)
			return queryset

@admin.register(NotificationUser)
class NotificationUserAdmin(ExportMixin, admin.ModelAdmin):
	list_display = ('get_notification_display', 'user', 'notification_client', 'rating', 'feedback', 'solved', 'viewed')
	list_filter = ('rating', 'feedback_sent', 'notification__type', 'viewed', 'notification', NotificationUserClientFilter)
	autocomplete_fields = ('notification', 'user')
	resource_class = NotificationUserResource
	search_fields = ('feedback', )
	date_hierarchy = 'created_at'
	ordering = ('-created_at', )
