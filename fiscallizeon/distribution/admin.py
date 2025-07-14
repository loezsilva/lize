from django.contrib import admin
from fiscallizeon.applications.models import Application

from fiscallizeon.distribution.models import Room, RoomDistribution, RoomDistributionStudent

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
	list_display = ('name', 'coordination', 'capacity', )
	list_filter = ('coordination__unity__name', )
	search_fields = ('name', )
	autocomplete_fields = ('coordination', )


@admin.register(RoomDistribution)
class RoomDistributionAdmin(admin.ModelAdmin):
	list_display = ('created_at', )
	readonly_fields = ('created_at', 'updated_at', )


admin.site.register(RoomDistributionStudent)