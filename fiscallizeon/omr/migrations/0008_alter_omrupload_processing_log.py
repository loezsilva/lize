# Generated by Django 3.2.4 on 2021-10-23 18:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('omr', '0007_alter_omrupload_processing_log'),
    ]

    operations = [
        migrations.AlterField(
            model_name='omrupload',
            name='processing_log',
            field=models.TextField(blank=True, default='', null=True, verbose_name='Resultado da operação'),
        ),
    ]
