from django.contrib import admin

from fiscallizeon.events.models import Event, TextMessage, QuestionErrorReport, ApplicationMessage


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'

@admin.register(TextMessage)
class TextMessageAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'sender', 'content')
    search_fields = ('content', )

@admin.register(ApplicationMessage)
class ApplicationMessageAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'sender', 'content')
    search_fields = ('content', )


@admin.register(QuestionErrorReport)
class QuestionErrorReportAdmin(admin.ModelAdmin):
    date_hierarchy = 'created_at'
    list_filter = ('question__coordinations__unity__client', 'status')
    autocomplete_fields = ['application', 'question', 'sender', ]


    def get_question(self, obj):
        return obj.question

    list_display = ('created_at', 'get_question', 'sender')
    search_fields = ('application__name',  )