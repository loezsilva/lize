from django.contrib import admin
from fiscallizeon.exports.models import Import
from simple_history.admin import SimpleHistoryAdmin


@admin.register(Import)
class ImportAdmin(SimpleHistoryAdmin):
	# list_filter = ('exam', )
	list_display = ['id', 'created_at', 'get_type_display', 'created_by', ]
	autocomplete_fields = ['created_by', ]
	readonly_fields = ['errors', ]
	date_hierarchy = 'created_at'