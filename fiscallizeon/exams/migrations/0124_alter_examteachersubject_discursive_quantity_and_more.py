# Generated by Django 4.0.6 on 2023-06-15 18:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0123_merge_20230601_2020'),
    ]

    operations = [
        migrations.AlterField(
            model_name='examteachersubject',
            name='discursive_quantity',
            field=models.IntegerField(blank=True, help_text='Quantidade de questões discursivas que poderão ser adicionada ao caderno', null=True, verbose_name='Discursivas'),
        ),
        migrations.AlterField(
            model_name='examteachersubject',
            name='objective_quantity',
            field=models.IntegerField(blank=True, help_text='Quantidade de questões objetivas que poderão ser adicionada ao caderno', null=True, verbose_name='Objetivas'),
        ),
        migrations.AlterField(
            model_name='historicalexamteachersubject',
            name='discursive_quantity',
            field=models.IntegerField(blank=True, help_text='Quantidade de questões discursivas que poderão ser adicionada ao caderno', null=True, verbose_name='Discursivas'),
        ),
        migrations.AlterField(
            model_name='historicalexamteachersubject',
            name='objective_quantity',
            field=models.IntegerField(blank=True, help_text='Quantidade de questões objetivas que poderão ser adicionada ao caderno', null=True, verbose_name='Objetivas'),
        ),
    ]
