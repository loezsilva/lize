from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from fiscallizeon.questions.models import BaseText, Question, QuestionOption, SugestionTags

class QuestionOptionInline(admin.TabularInline):
    model = QuestionOption
    max_num = 5

@admin.register(Question)
class QuestionAdmin(SimpleHistoryAdmin):
    search_fields = ['enunciation', 'pk']
    readonly_fields = ['topic', 'abilities', 'competences', 'source_question', 'created_by']
    list_filter = ['is_public', 'is_abstract',]
    list_display = ['pk', 'enunciation', 'created_at']
    inlines = [
        QuestionOptionInline
    ]
    autocomplete_fields = ("coordinations", "subject", "grade", "topics")


@admin.register(QuestionOption)
class QuestionOptionAdmin(admin.ModelAdmin):
    list_display = ['id', 'text', 'is_correct']
    search_fields = ("question__enunciation", 'text')

@admin.register(BaseText)
class BaseTextAdmin(admin.ModelAdmin):
    '''Admin View for BaseText'''
    list_display = ('title', 'created_by')
    search_fields = ('title',)
    date_hierarchy = 'created_at'
    autocomplete_fields = ('created_by', )
    ordering = ('-created_at',)

@admin.register(SugestionTags)
class SugestionTagsAdmin(admin.ModelAdmin):
    '''Admin View for SugestionTags'''

    list_display = ('label',)
    search_fields = ('label', 'text')
    date_hierarchy = 'created_at'
    autocomplete_fields = ('user',)
    ordering = ('-created_at',)