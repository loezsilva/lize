# Generated by Django 4.0.6 on 2023-08-30 16:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0101_merge_20230821_1730'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='has_followup_dashboard',
            field=models.BooleanField(default=False, verbose_name='Tem acesso ao dashboard de acompanhamento'),
        ),
    ]
