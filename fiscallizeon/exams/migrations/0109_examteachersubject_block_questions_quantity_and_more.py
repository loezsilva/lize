# Generated by Django 4.0.6 on 2022-11-30 15:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0108_merge_20221127_1104'),
    ]

    operations = [
        migrations.AddField(
            model_name='examteachersubject',
            name='block_questions_quantity',
            field=models.BooleanField(default=False, verbose_name='Definir quantidade de questões objectivas/discursivas'),
        ),
        migrations.AddField(
            model_name='examteachersubject',
            name='discursive_quantity',
            field=models.IntegerField(default=1, help_text='Quantidade de questões discursivas que poderão ser adicionada ao caderno', verbose_name='Discursivas'),
        ),
        migrations.AddField(
            model_name='examteachersubject',
            name='objective_quantity',
            field=models.IntegerField(default=1, help_text='Quantidade de questões objetivas que poderão ser adicionada ao caderno', verbose_name='Objetivas'),
        ),
        migrations.AddField(
            model_name='historicalexamteachersubject',
            name='block_questions_quantity',
            field=models.BooleanField(default=False, verbose_name='Definir quantidade de questões objectivas/discursivas'),
        ),
        migrations.AddField(
            model_name='historicalexamteachersubject',
            name='discursive_quantity',
            field=models.IntegerField(default=1, help_text='Quantidade de questões discursivas que poderão ser adicionada ao caderno', verbose_name='Discursivas'),
        ),
        migrations.AddField(
            model_name='historicalexamteachersubject',
            name='objective_quantity',
            field=models.IntegerField(default=1, help_text='Quantidade de questões objetivas que poderão ser adicionada ao caderno', verbose_name='Objetivas'),
        ),
    ]
