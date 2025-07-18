# Generated by Django 4.0.6 on 2022-11-21 18:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0101_remove_exam_automatic_creation_remove_exam_priority_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='exam',
            name='level',
            field=models.PositiveIntegerField(blank=True, choices=[(1, 'Ensino Fundamental 1'), (2, 'Ensino Fundamental 2'), (0, 'Ensino Médio')], null=True, verbose_name='Etapa do Ensino'),
        ),
        migrations.AddField(
            model_name='historicalexam',
            name='level',
            field=models.PositiveIntegerField(blank=True, choices=[(1, 'Ensino Fundamental 1'), (2, 'Ensino Fundamental 2'), (0, 'Ensino Médio')], null=True, verbose_name='Etapa do Ensino'),
        ),
    ]
