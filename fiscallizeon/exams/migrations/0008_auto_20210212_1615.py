# Generated by Django 3.0.7 on 2021-02-12 19:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0006_auto_20210212_1511'),
        ('exams', '0007_remove_exam_coordination'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exam',
            name='coordinations',
            field=models.ManyToManyField(related_name='exams', to='clients.SchoolCoordination', verbose_name='Coordenações autorizadas'),
        ),
    ]
