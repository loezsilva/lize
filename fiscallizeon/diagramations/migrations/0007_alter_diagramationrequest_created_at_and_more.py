# Generated by Django 4.0.2 on 2022-04-19 14:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('diagramations', '0006_alter_diagramationrequest_options'),
    ]

    operations = [
        migrations.AlterField(
            model_name='diagramationrequest',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Registrado em'),
        ),
        migrations.AlterField(
            model_name='diagramationrequest',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, db_index=True, verbose_name='Atualizado em'),
        ),
    ]
