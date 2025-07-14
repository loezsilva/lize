from django.contrib import admin
from fiscallizeon.bncc.models import Abiliity, Competence, KnowledgeObject, ThematicUnit, LanguagePractice, ActingField, Axis

admin.site.register([KnowledgeObject, ThematicUnit, LanguagePractice, ActingField, Axis])


@admin.register(Competence)
class CompetenceAdmin(admin.ModelAdmin):
    list_display = ('text', 'code', 'knowledge_area')
    list_filter = ('knowledge_area', 'client')
    search_fields = ('text', 'code')
    autocomplete_fields = ('client', 'subject', 'knowledge_area', 'created_by')
    
@admin.register(Abiliity)
class CompetenceAdmin(admin.ModelAdmin):
    list_display = ('text', 'code', 'knowledge_area')
    list_filter = ('knowledge_area', 'client')
    search_fields = ('text', 'code')
    autocomplete_fields = ('client', 'subject', 'knowledge_area', 'created_by')