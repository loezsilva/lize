# Generated by Django 3.0.7 on 2021-03-25 16:17

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0010_auto_20210311_1524'),
        ('exams', '0027_auto_20210323_1027'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exam',
            name='coordinations',
            field=models.ManyToManyField(related_name='exams', to='clients.SchoolCoordination', verbose_name='Coordenações autorizadas a acessar essa prova'),
        ),
        migrations.AlterField(
            model_name='exam',
            name='status',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Elaborando'), (1, 'Aberta'), (2, 'Fechada')], default=0, verbose_name='Situação da prova'),
        ),
    ]
