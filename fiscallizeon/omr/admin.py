from django.contrib import admin

from fiscallizeon.omr.models import OMRCategory, OMRUpload, OMRStudents, OMRError, OMRDiscursiveError, OMRDiscursiveScan


class OMRDiscursiveErrorInline(admin.TabularInline):
	model = OMRDiscursiveError
	readonly_fields = ['application_student', 'error_image']

class OMRErrorInline(admin.TabularInline):
	model = OMRError
	readonly_fields = ['error_image', 'page_number', 'student', 'application']

class OMRDiscursiveScanInline(admin.TabularInline):
	model = OMRDiscursiveScan
	readonly_fields = []

class OMRStudentsInline(admin.TabularInline):   
	model = OMRStudents  
	readonly_fields = ['application_student', 'scan_image', 'successful_questions_count', 'checked_by']

@admin.register(OMRUpload)
class OMRUploadAdmin(admin.ModelAdmin):
	list_display = ('pk', 'created_at', 'user', 'get_status_display')
	search_fields = ('user__name', )
	autocomplete_fields = ('user', 'application', 'school_class', 'deleted_by')
	exclude_fields = ['student', ]
	inlines = [
		OMRStudentsInline,
		OMRErrorInline,
		OMRDiscursiveErrorInline,
	]

@admin.register(OMRCategory)
class OMRCategoryAdmin(admin.ModelAdmin):
	list_display = ('name', 'sequential', 'is_native', 'is_discursive')

@admin.register(OMRStudents)
class OMRStudentsAdmin(admin.ModelAdmin):
	readonly_fields = ['upload', 'application_student', 'checked_by']
	inlines = [
		OMRDiscursiveScanInline,
	]