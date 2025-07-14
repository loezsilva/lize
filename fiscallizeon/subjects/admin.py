from django.contrib import admin

from fiscallizeon.subjects.models import KnowledgeArea, Subject, Topic, MainTopic, Theme

@admin.register(KnowledgeArea)
class KnowledgeAreaAdmin(admin.ModelAdmin):
    search_fields = ("name", )

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    search_fields = ("name", )
    autocomplete_fields = ("knowledge_area", "parent_subject", "client")
    readonly_fields = ("created_by", )


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    search_fields = ('name',)
    readonly_fields = ('created_by',)
    autocomplete_fields = ('client', 'grade', 'subject')


@admin.register(MainTopic)
class MainTopicAdmin(admin.ModelAdmin):
    readonly_fields = ('created_by',)
    autocomplete_fields = ('client',)


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    readonly_fields = ('created_by',)
    autocomplete_fields = ('client',)
    search_fields = ("name", )
