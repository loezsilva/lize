# Generated by Django 4.0.6 on 2024-01-31 21:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0013_alter_user_default_ai_credits'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_freemium',
            field=models.BooleanField(blank=True, default=False, verbose_name='Esta no ambiente freemium'),
        ),
    ]
