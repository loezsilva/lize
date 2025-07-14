from django.contrib import admin

# Register your models here.
from django.contrib import admin

from fiscallizeon.diagramations.models import DiagramationRequest

@admin.register(DiagramationRequest)
class DiagramationRequestAdmin(admin.ModelAdmin):
	list_display = ('created_by', 'application_date', 'status')
	list_filter = ('application_date', 'grade', 'status')
	date_hierarchy = 'application_date'
	autocomplete_fields = ('created_by', )