from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.core.cache import cache
from django.db import transaction
from django.http import HttpResponseRedirect
from django.shortcuts import resolve_url as r
from django.urls import reverse
from django.utils.safestring import mark_safe

from fiscallizeon.clients.models import (
    Client, CoordinationMember, ExamPrintConfig, Mensality, Partner, QuestionTag, SchoolCoordination, Unity, ClientCustomFilter, TeachingStage, EducationSystem, ConfigNotification
)
from fiscallizeon.classes.models import SchoolClass

from dateutil.relativedelta import relativedelta
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from django.contrib import messages


admin.site.register([TeachingStage, EducationSystem, ConfigNotification])


@staff_member_required
def admin_hijack_client(request, pk):
    try:
        with transaction.atomic():
            request.user.coordination_member.all().delete()

            for coordination in SchoolCoordination.objects.using('default').filter(unity__client_id=pk):
                CoordinationMember.objects.get_or_create(
                    user=request.user,
                    coordination=coordination,
                    is_coordinator=True,
                    is_reviewer=True,
                    is_pedagogic_reviewer=True,
                )

            cache.delete_many([
                f'USER_COORDINATIONS_{request.user.pk}',
                f'USER_CLIENTS_{request.user.pk}',
                f'CLIENT_MODULES_{request.user.pk}',
                f'USER_CLIENTS_OBJ_{request.user.pk}',
            ])

        messages.success(request, 'Cliente aderido com sucesso.')
    except Exception:
        messages.error(request, 'Ocorreu um erro ao tentar aderir ao cliente.')

    keep = request.GET.get('keep', False)
    if keep:
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    return HttpResponseRedirect(reverse('admin:clients_client_changelist'))


@admin.action(description='Recalcular o dash de acompanhamento')
def generate_performances_followup_dashboard(modeladmin, request, queryset):
	for client in queryset:
		client.run_recalculate_followup_task()
	messages.success(request, "Em breve o calculo será finalizado.")
	


class SchoolCoordinationInline(admin.TabularInline):
	model = SchoolCoordination
	extra = 1
	show_change_link = True
	
class UnityInline(admin.TabularInline):
	model = Unity
	extra = 1
	show_change_link = True

class SchoolClassInline(admin.TabularInline):
	model = SchoolClass
	extra = 1
	show_change_link = True
	autocomplete_fields = ("coordination", "students", )
	readonly_fields = ("coordination", "students", )

class MensalityInline(admin.TabularInline):
	model = Mensality
	extra = 1
	show_change_link = True

class QuestionTagInline(admin.TabularInline):
	model = QuestionTag
	extra = 1
	show_change_link = True

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
	list_display = (
		'name',
		'type_client',
		'plan',
		'status',
		'monthly_ticket',
		'get_last_application_date',
		'can_request_ai_questions'
	)
	list_filter = ('plan', 'status')
	search_fields = ('name', 'pk',)
	inlines = [
		UnityInline,
		MensalityInline,
		QuestionTagInline,
	]
	actions = [generate_performances_followup_dashboard]

	def hijack_button(self, request, obj):
		if not request.user.is_superuser:
			return ' '

		return mark_safe(
			f'<a href="{r("clients:admin-hijack-client", obj.pk)}" class="button">HIJACK</a>'
		)

	def get_changelist_instance(self, request):
		# We inject the request for the CSRF token, see also:
		# https://code.djangoproject.com/ticket/13659
		def hijack_field(obj):
			return self.hijack_button(request, obj)

		hijack_field.short_description = "cliente do hijack"

		# we
		list_display = [*self.get_list_display(request), hijack_field]
		# Same as super method, see also:
		# https://github.com/django/django/blob/76c0b32f826469320c59709d31e2f2126dd7c505/django/contrib/admin/options.py#L724-L750
		list_display_links = self.get_list_display_links(request, list_display)
		# Add the action checkboxes if any actions are available.
		if self.get_actions(request):
				list_display = ["action_checkbox", *list_display]
		sortable_by = self.get_sortable_by(request)
		ChangeList = self.get_changelist(request)
		args = [
				request,
				self.model,
				list_display,
				list_display_links,
				self.get_list_filter(request),
				self.date_hierarchy,
				self.get_search_fields(request),
				self.get_list_select_related(request),
				self.list_per_page,
				self.list_max_show_all,
				self.list_editable,
				self,
				sortable_by,
				self.search_help_text,
		]
		return ChangeList(*args)

@admin.register(CoordinationMember)
class CoordinationMemberAdmin(admin.ModelAdmin):
	list_display = ('user', 'coordination', 'is_coordinator', 'is_reviewer', 'is_pedagogic_reviewer', 'created_at',)
	search_fields = ('user__username', 'coordination__name')
	list_filter = ('coordination__unity__client',)
	autocomplete_fields = ('user',)
	ordering = ('-created_at',)

@admin.register(Unity)
class UnityAdmin(admin.ModelAdmin):
	search_fields = ('name', )
	inlines = [
		SchoolCoordinationInline
	]


@admin.register(SchoolCoordination)
class CoordinantionAdmin(admin.ModelAdmin):
	search_fields = ("name", )
	autocomplete_fields = ("unity", )
	inlines = [SchoolClassInline, ]


@admin.register(ExamPrintConfig)
class ExamPrintConfigAdmin(admin.ModelAdmin):
    search_fields = ('name', 'client__name',)
    autocomplete_fields = ('header', 'client')
    
@admin.register(ClientCustomFilter)
class ClientCustomFilterAdmin(admin.ModelAdmin):
	list_display = ('user', 'name', 'url')
	search_fields = ('user', 'name', 'url')

class MensalityResource(resources.ModelResource):
	class Meta:
		model = Mensality

@admin.action(description='Marcar mensalidades como pagas')
def activate_mensality(modeladmin, request, queryset):
	queryset.update(status=Mensality.ACTIVE)

@admin.action(description='Renovar mensalidades')
def activate_mensality(modeladmin, request, queryset):
	for mensality in queryset:
		mensality.billing_date = mensality.billing_date + relativedelta(months=1)
		mensality.save(skip_hooks=True)

@admin.action(description='Duplicar mensalidades selecionadas para o mês seguinte') 
def duplicate_mensality(modeladmin, request, queryset):
	for mensality in queryset:
		mensality_nextmonth = Mensality(
			client=mensality.client,
			status=mensality.status,
			value=mensality.value,
			billing_date=mensality.billing_date + relativedelta(months=1),
		)
		mensality_nextmonth.save(skip_hooks=True)

@admin.register(Mensality)
class MensalityAdmin(ImportExportModelAdmin):
	list_display = ('client', 'get_client_plan', 'status', 'value', 'billing_date')
	search_fields = ('client__name',)
	list_filter = ('status', 'client__plan')
	actions = [activate_mensality, duplicate_mensality,]
	date_hierarchy = 'billing_date'
	resource_class = MensalityResource

@admin.register(QuestionTag)
class QuestionTagAdmin(admin.ModelAdmin):
	list_display = ('name',)
	search_fields = ('name',)

@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
	list_display = ('user', 'client')
	search_fields = ('user',)
	autocomplete_fields = ('user', )