# Generated by Django 4.0.6 on 2023-10-09 20:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('classes', '0021_schoolclass_logo_schoolclass_slug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='grade',
            name='level',
            field=models.PositiveIntegerField(choices=[(1, 'Anos iniciais'), (2, 'Anos finais'), (0, 'Ensino Médio')], db_index=True, verbose_name='Ensino'),
        ),
    ]
