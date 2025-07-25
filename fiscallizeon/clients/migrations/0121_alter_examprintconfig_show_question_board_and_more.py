# Generated by Django 4.0.6 on 2024-03-29 14:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0120_merge_20240329_1135'),
    ]

    operations = [
        migrations.AlterField(
            model_name='examprintconfig',
            name='show_question_board',
            field=models.BooleanField(default=False, help_text='Designa se o caderno deve mostrar a banca das questões.', verbose_name='mostrar a banca das questões?'),
        ),
        migrations.AlterField(
            model_name='examprintconfig',
            name='show_question_score',
            field=models.BooleanField(default=False, help_text='Designa se o caderno deve mostrar a pontuação das questões.', verbose_name='mostrar a pontuação das questões?'),
        ),
    ]
