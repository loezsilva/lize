from django.contrib import admin
from ..accounts.models import User

from fiscallizeon.classes.models import SchoolClass, Grade, CourseType, Stage, Course
from django.contrib import messages


@admin.action(description='Desativar todos os alunos das turmas selecionadas')
def unactive_students(modeladmin, request, queryset):
	for classe in queryset:
		User.objects.filter(student__in=classe.students.all()).update(is_active=False)
	messages.success(request, "Os alunos foram desativados com sucesso.")

@admin.action(description='Ativar todos os alunos das turmas selecionadas')
def active_students(modeladmin, request, queryset):
	for classe in queryset:
		User.objects.filter(student__in=classe.students.all()).update(is_active=True)
	messages.success(request, "Os alunos foram ativados com sucesso.")

@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
	list_display = ('name', 'id_erp', 'school_year', 'is_itinerary', )
	list_filter = ('school_year', 'coordination__unity__client', )
	search_fields = ('name', 'id_erp', 'id', )
	readonly_fields = ['created_at', 'updated_at', ]
	autocomplete_fields=('coordination', 'students')
	actions = [unactive_students, active_students]

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
	list_display = ('name', 'get_level_display')
	search_fields = ('name', )

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
	list_display = ('name', )
	search_fields = ('name', )

@admin.register(CourseType)
class CourseTypeAdmin(admin.ModelAdmin):
	list_display = ('name', )
	search_fields = ('name', )
	
@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
	list_display = ('name', )
	search_fields = ('name', )

