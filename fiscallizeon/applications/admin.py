from django.contrib import admin
from django.contrib.admin.views.autocomplete import AutocompleteJsonView

from fiscallizeon.applications.models import (
    Application, ApplicationStudent, Annotation, ApplicationAnnotation, ApplicationNotice, 
	RandomizationVersion, HashAccess, ApplicationDeadlineCorrectionResponseException,
	ApplicationRandomizationVersion, ApplicationType
)
from fiscallizeon.applications.forms import ApplicationForm

from fiscallizeon.inspectors.models import Inspector
import hashlib

from django.contrib import messages

admin.site.register([Annotation, ApplicationAnnotation, ApplicationNotice])


@admin.action(description='Recalcular os dados do dash de acompanhamento')
def generate_performances_followup_dashboard(modeladmin, request, queryset):
	for application in queryset:
		application.run_recalculate_followup_task()
	messages.success(request, "Em breve o calculo será finalizado.")

defaul_queryset = AutocompleteJsonView.get_queryset
def queryset_custom(self):
    qs = self.model_admin.get_queryset(self.request)
    qs = qs.complex_filter(self.source_field.get_limit_choices_to())
    qs, search_use_distinct = self.model_admin.get_search_results(self.request, qs, self.term)

    if self.request.GET.get('field_name') == 'inspectors':
        qs = qs.filter(inspector_type=Inspector.INSPECTOR, coordinations__isnull=True)

    if search_use_distinct:
        qs = qs.distinct()

    return qs
class ApplicationStudentInline(admin.TabularInline):   
	model = ApplicationStudent  
	fields = ['student', ]

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
	list_display = ('pk', 'created_at', 'date', 'start', 'end', 'prefix')
	date_hierarchy = 'date'
	list_filter = ('school_classes__coordination__unity__client__name', 'category', 'inspectors__name')
	search_fields = ('exam__name', 'pk', 'exam__pk')
	autocomplete_fields = ('exam', 'inspectors', 'school_classes')
	actions = [generate_performances_followup_dashboard]

	def get_form(self, request, obj, change=None, **kwargs):
		if obj.inspectors_fiscallize:
			AutocompleteJsonView.get_queryset = queryset_custom
		else:
			AutocompleteJsonView.get_queryset = defaul_queryset
		return super().get_form(request, obj, change, **kwargs)


@admin.register(ApplicationStudent)
class ApplicationStudentAdmin(admin.ModelAdmin):
	list_filter = ('student__client', )
	list_display = ('student', 'application_date', 'start_time', 'end_time',)
	ordering = ('-created_at', )
	date_hierarchy = 'application__date'
	search_fields = ('student__name', 'application__pk',)
	readonly_fields = ('created_at', 'updated_at', )
	autocomplete_fields = ('student', 'duplicated_answers', 'application', 'empty_option_questions',)

	def application_date(self, obj):
		return obj.application.date

	application_date.short_description = 'Data da aplicação'

@admin.register(RandomizationVersion)
class RandomizationVersionAdmin(admin.ModelAdmin):  
	autocomplete_fields = ('application_student', )
	list_display = ("application_student", "version_number", "created_at",)
	ordering = ('-version_number', )
	search_fields = ('application_student__student__name', )
	readonly_fields = ('created_at', 'exam_json', 'version_number', )

@admin.register(ApplicationRandomizationVersion)
class ApplicationRandomizationVersionAdmin(admin.ModelAdmin):
	autocomplete_fields = ('application', )
	list_display = ("application", "version_number", "sequential", "created_at",)
	ordering = ('-version_number', 'sequential')
	search_fields = ('application__exam__name', )
	readonly_fields = ('created_at', 'exam_json', 'version_number', 'exam_hash')
 
@admin.register(HashAccess)
class HashAccessAdmin(admin.ModelAdmin):
	list_display = ("application_student", "pk", "validity")
	readonly_fields  = ("application_student",) 

@admin.register(ApplicationDeadlineCorrectionResponseException)
class ApplicationDeadlineCorrectionResponseExceptionAdmin(admin.ModelAdmin):
	list_display = ('application', 'teacher', 'date', 'created_at')
	search_fields = ('application__exam__name', 'teacher__name')
	autocomplete_fields = ('application', 'teacher')

@admin.register(ApplicationType)
class ApplicationTypeAdmin(admin.ModelAdmin):
	list_display = ('name', 'created_at', 'updated_at')
	search_fields = ('name',)
	readonly_fields = ('created_at', 'updated_at')
	