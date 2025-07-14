from django.contrib import admin
"""
from .models import Dashboard, DashboardChart
# Register your models here.

@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    '''Admin View for Dashboard'''

    list_display = ('name', 'client')
    search_fields = ('name',)
    date_hierarchy = 'created_at'
    autocomplete_fields = ('created_by', 'client')
    ordering = ('-created_at',)

@admin.register(DashboardChart)
class DashboardChartAdmin(admin.ModelAdmin):
    '''Admin View for DashboardChart'''

    list_display = ('dashboard', 'who', 'what', 'order')
    list_filter = ('who', 'what')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

"""