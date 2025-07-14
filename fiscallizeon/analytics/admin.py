from django.contrib import admin
from fiscallizeon.analytics.models import ApplicationStudentLevelQuestion, GenericPerformances, ClassSubjectApplicationLevel, \
	GenericPerformancesFollowUp, MetabaseDashboard

@admin.register(GenericPerformances)
class GenericPerformancesAdmin(admin.ModelAdmin):
	list_display = ('application_student', 'performance')
	readonly_fields = ['application_student', 'exam', 'school_class']
	search_fields = ('object_id', )
	ordering = ('-created_at', )

@admin.register(GenericPerformancesFollowUp)
class GenericPerformancesFollowUpAdmin(admin.ModelAdmin):
	list_display = ('deadline', 'school_class', 'unity', 'object_id', 'total', 'quantity', 'cards_total', 'cards_quantity')
	list_filter = ('deadline',)
	# readonly_fields = ['school_class', 'unity', 'object_id', 'total', 'quantity']
	# search_fields = ('school_class', 'unity', 'object_id')
	autocomplete_fields = ('school_class', 'unity', 'inspectors', 'coordination', 'objective_examquestions', 'discursive_examquestions')
	ordering = ('-created_at', )

@admin.register(ApplicationStudentLevelQuestion)
class ApplicationStudentLevelQuestionAdmin(admin.ModelAdmin):
	list_display = ('application_student','get_exam_name', 'teacher_subject', 'performance')
	readonly_fields = ['application_student', 'performance', 'teacher_subject', 'level']


@admin.register(ClassSubjectApplicationLevel)
class ClassSubjectApplicationLevelAdmin(admin.ModelAdmin):
	date_hierarchy = 'application__date'
	list_filter = ('school_class__coordination__unity__client__name',)
	list_display = ('application', 'get_exam_name', 'school_class', 'teacher_subject', 'performance')
	readonly_fields = ['application', 'performance', 'teacher_subject', 'level', 'school_class']

@admin.register(MetabaseDashboard)
class MetabaseDashboardAdmin(admin.ModelAdmin):
	list_display = ('client', 'name', 'short_name')
	readonly_fields = ['created_at', 'updated_at']
	search_fields = ('name', )
	ordering = ('-created_at', )
	autocomplete_fields = ('client',)