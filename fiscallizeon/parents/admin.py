from django.contrib import admin
from .models import Parent
from django.contrib import messages
from django.urls import reverse
from django.utils.html import format_html

@admin.action(description='Reenvia email para o pai criar conta na Fiscallize')
def resend_email_to_parent(modeladmin, request, queryset):
	for parent in queryset:
		parent.send_mail_to_first_access()
	messages.success(request, "Ação concluída com sucesso, foi enviado um email para cada um dos pais selecionados.")
	
# Register your models here.
@admin.register(Parent)
class ParentAdmin(admin.ModelAdmin):
	'''Admin View for Parent'''

	list_display = ('email', 'user', 'link_de_cricao')
	list_filter = ('email',)
	search_fields = ('email', 'user__name')
	autocomplete_fields = ('user', 'students')
	ordering = ('-created_at',)
	actions = [resend_email_to_parent]

	def link_de_cricao(self, obj):
		if obj.user:
			return 'Já tem usuário'
		return format_html("<a href='{url}' target='_blank'>Link de criação do usuário</a>", url=obj.urls.get('user_creation'))