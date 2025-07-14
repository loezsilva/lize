# Criado manualmente
import os
import json

from django.db import migrations
from django.conf import settings

def create_omr_categories(apps, schema_editor):
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('omr', '0024_remove_omrcategory_supports_dettached_and_more'),
    ]

    operations = [
        migrations.RunPython(create_omr_categories, reverse_code=migrations.RunPython.noop),
    ]