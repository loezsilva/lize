# Generated by Django 4.0.6 on 2024-07-22 17:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0022_alter_user_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='onboarding_responsible',
            field=models.BooleanField(default=False, verbose_name='responsável pela integração?'),
        ),
    ]
