# Generated by Django 4.0.2 on 2022-04-20 20:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_alter_config_created_at_alter_config_updated_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='config',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Atualizado em'),
        ),
    ]
