# Generated by Django 4.2.18 on 2025-02-12 12:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0030_historicaluser_has_app_access_user_has_app_access'),
    ]

    operations = [
        migrations.RenameField(
            model_name='historicaluser',
            old_name='has_app_access',
            new_name='can_access_app',
        ),
        migrations.RenameField(
            model_name='user',
            old_name='has_app_access',
            new_name='can_access_app',
        ),
    ]
