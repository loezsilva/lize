# Generated by Django 4.0.6 on 2023-06-13 23:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('parents', '0003_alter_parent_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='parent',
            options={'verbose_name': 'Responsável', 'verbose_name_plural': 'Responsáveis'},
        ),
    ]
