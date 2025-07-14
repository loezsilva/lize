from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group

from import_export import resources
from import_export.fields import Field
from import_export.admin import ImportExportModelAdmin
from simple_history.admin import SimpleHistoryAdmin

from fiscallizeon.accounts.models import User, CustomGroup, SSOTokenUser
from fiscallizeon.clients.models import Client, CoordinationMember, Partner
from fiscallizeon.inspectors.models import Inspector
from django.db.models import Q

admin.site.unregister(Group)

@admin.register(CustomGroup)
class CustomGroupAdmin(admin.ModelAdmin):
    filter_horizontal = ("permissions",)
    list_display = ("name", "client", "default")
    list_filter = ("client", "default")
    search_fields = ("name",)
    
class CoordinationMemberInline(admin.TabularInline):
	model = CoordinationMember
	extra = 1
	show_change_link = True
	autocomplete_fields=("coordination", )

class PartnerInline(admin.TabularInline):
	model = Partner
	extra = 1
	autocomplete_fields = ("client", )

class UserFilter(SimpleListFilter):
    title = 'Tipo de Usuário'
    parameter_name = 'user_type'

    def lookups(self, request, model_admin):
        return [
			('inspector', 'Fiscal'),
			('student', 'Aluno'),
			('teacher', 'Professor'),
			('coordination', 'Coordenação'),
			('parent', 'Responsável'),
			('partner', 'Parceiro'),
		]

    def queryset(self, request, queryset):
        if not self.value():
            return queryset

        if self.value() == 'inspector':
            return queryset.filter(
                inspector__isnull=False,
                coordination_member__isnull=True,
                inspector__inspector_type=Inspector.INSPECTOR
            ).distinct()
        elif self.value() == 'student':
            return queryset.filter(student__isnull=False).distinct()
        elif self.value() == 'teacher':
            return queryset.filter(
                inspector__isnull=False,
                coordination_member__isnull=True,
                inspector__inspector_type=Inspector.TEACHER
            ).distinct()
        elif self.value() == 'parent':
            return queryset.filter(
                parent__isnull=False
            ).distinct()
        elif self.value() == 'partner':
            return queryset.filter(
                partner__isnull=False
            ).distinct()
        else:
            return queryset.filter(
                coordination_member__isnull=False,
                inspector__isnull=True,
            ).distinct()

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
			return queryset.filter(
				Q(student__client__pk=self.value())|
				Q(inspector__coordinations__unity__client__pk=self.value())|
				Q(coordination_member__coordination__unity__client__pk=self.value())|
				Q(parent__students__client__pk=self.value())
			).distinct()
		
		return
class UserExportResource(resources.ModelResource):
	get_user_function = Field()
	get_user_classes = Field()
	get_user_coordinations = Field()
	get_user_ra = Field()

	class Meta:
		model = User
		fields = ('name', 'email', 'is_active', 'get_user_function', 'get_user_classes', 'get_user_coordinations', 'get_user_ra')

	def dehydrate_get_user_function(self, user):
		return user.get_user_function
        
	def dehydrate_get_user_classes(self, user):
		return user.get_user_classes

	def dehydrate_get_user_coordinations(self, user):
		return user.get_user_coordinations

	def dehydrate_get_user_ra(self, user):
		return user.get_user_ra

@admin.register(User)
class UserAdmin(UserAdmin, ImportExportModelAdmin, SimpleHistoryAdmin):
	list_display = ('__str__', 'email', 'username', 'user_type_display', 'date_joined', 'get_clients_display', 'is_active')
	search_fields = ('name', 'student__name', 'email', 'username', )
	autocomplete_fields = ['custom_groups']
	resource_class = UserExportResource
	inlines = [
		CoordinationMemberInline,
		PartnerInline,
	]
	exclude = ['groups']
	list_filter = (UserFilter, ClientFilter)
	fieldsets = (
		(None, {"fields": ("username", "password")}),
		(("Informações do usuário"), {"fields": ("name", "email", "two_factor_enabled")}),
		(
			("Permissions"),
			{
				"fields": (
					"is_active",
					"is_staff",
					"is_superuser",
					"custom_groups",
					"user_permissions",
					"must_change_password",
					"onboarding_responsible",
					"can_request_ai_questions",
					"can_access_app",
				),
			},
		),
		(("Datas importantes"), {"fields": ("last_login", "date_joined")}),
		(("Outras informações"), {"fields": ("nickname", "avatar", "color_mode_theme", "has_viewed_starter_onboarding", "mood")}),
	)
	add_fieldsets = (
		(
			None,
			{
				"classes": ("wide",),
				"fields": ("email", "password1", "password2"),
			},
		),
	)

@admin.register(SSOTokenUser)
class SSOTokenUserAdmin(admin.ModelAdmin):
	autocomplete_fields = ('user',)
	readonly_fields = ('user', 'access_token', 'refresh_token', )