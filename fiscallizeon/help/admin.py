from django.contrib import admin

from fiscallizeon.help.models import HelpLink, Tutorial, TutorialCategory

from .forms import HelpForm
from .models import TutorialFeedback


admin.site.register([TutorialCategory])


@admin.register(HelpLink)
class HelpLinkAdmin(admin.ModelAdmin):
	list_display = ('article_name', 'url_path',)
	search_fields = ('article_name', )


@admin.register(Tutorial)
class TutorialAdmin(admin.ModelAdmin):
	list_display = ('title', 'feedback_positive', 'feedback_negative')
	search_fields = ('title', )

	def feedback_positive(self, obj):
		return obj.feedbacks.filter(value__exact=TutorialFeedback.POSITIVE).count()

	feedback_positive.short_description = 'likes'

	def feedback_negative(self, obj):
		return obj.feedbacks.filter(value__exact=TutorialFeedback.NEGATIVE).count()

	feedback_negative.short_description = 'dislikes'


@admin.register(TutorialFeedback)
class TutorialFeedbackAdmin(admin.ModelAdmin):
	list_display = ('tutorial', 'user', 'value', 'date', 'created_at')
	date_hierarchy = 'date'
	search_fields = ('tutorial', 'user')
	list_filter = ('value',)
	readonly_fields = ('date',)
	autocomplete_fields = ('tutorial', 'user')
