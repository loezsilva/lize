# Generated by Django 4.0.6 on 2025-01-22 14:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0151_merge_20250110_2216'),
    ]

    operations = [
        migrations.AlterField(
            model_name='educationsystem',
            name='unities',
            field=models.ManyToManyField(blank=True, to='clients.unity', verbose_name='Unidades'),
        ),
    ]
