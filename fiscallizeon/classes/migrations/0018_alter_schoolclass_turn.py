# Generated by Django 4.0.6 on 2022-10-11 02:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('classes', '0017_alter_grade_level'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schoolclass',
            name='turn',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(0, 'Manhã'), (1, 'Tarde'), (2, 'Noite'), (3, 'Integral')], null=True, verbose_name='Turno'),
        ),
    ]
