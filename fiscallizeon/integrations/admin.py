from django.contrib import admin

from fiscallizeon.integrations.models import Integration, SubjectCode, TopicCode, AbilityCode, \
    CompetenceCode, NotesMigrationProof, IntegrationToken


class IntegrationTokenInline(admin.StackedInline):
    model = IntegrationToken
    extra = 0
    
@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    '''Admin View for Integration'''

    list_display = ('client', 'erp', 'school_code', 'chave')
    list_filter = ('erp',)
    inlines = [IntegrationTokenInline]
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    def chave(self, obj):
        if obj.erp == Integration.ACTIVESOFT:
            if token := obj.tokens.order_by('created_at').first():
                return token.token
            else:
                obj.token
            
        return obj.token

@admin.register(NotesMigrationProof)
class NotesMigrationProofAdmim(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    autocomplete_fields = ('exam', 'students', 'created_by')
    list_display = ('code', 'created_by', 'created_at')
    search_fields = ('created_by__name',)

@admin.register(SubjectCode)
class SubjectCodeAdmin(admin.ModelAdmin):
	list_filter = ('client', )
	list_display = ['client', 'subject', 'code', 'created_at']
	search_fields = ('subject__name', 'code', )
	ordering = ('-created_at',)
	autocomplete_fields = ['subject', 'created_by']

@admin.register(TopicCode)
class TopicCodeAdmin(admin.ModelAdmin):
	list_filter = ('client', )
	list_display = ['client', 'created_at']
	search_fields = ('topic__name', 'code', )
	ordering = ('-created_at',)
	autocomplete_fields = ['topic', 'created_by']

@admin.register(AbilityCode)
class AbilityCodeAdmin(admin.ModelAdmin):
	list_filter = ('client', )
	list_display = ['client', 'created_at']
	search_fields = ('ability__text', 'code', )
	ordering = ('-created_at',)
	autocomplete_fields = ['ability', 'created_by']
	
@admin.register(CompetenceCode)
class CompetenceCodeAdmin(admin.ModelAdmin):
	list_filter = ('client', )
	list_display = ['client', 'created_at']
	search_fields = ('competence__text', 'code', )
	ordering = ('-created_at',)
	autocomplete_fields = ['competence', 'created_by']