from rest_framework.authtoken.admin import TokenAdmin

from django.contrib import admin

from fiscallizeon.core.models import Config

admin.site.register(Config)

TokenAdmin.raw_id_fields = ['user']