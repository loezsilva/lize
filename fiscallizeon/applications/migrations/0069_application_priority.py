# Generated by Django 4.0.6 on 2022-10-24 19:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0068_alter_application_automatic_creation'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='priority',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Baixa'), (1, 'Média'), (2, 'Alta')], default=0, verbose_name='Prioridade'),
        ),
    ]
