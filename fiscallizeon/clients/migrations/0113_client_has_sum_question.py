# Generated by Django 4.0.6 on 2024-01-25 12:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0112_merge_20231206_2030'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='has_sum_question',
            field=models.BooleanField(default=False, verbose_name='Tem acesso a questões de somatória'),
        ),
    ]
