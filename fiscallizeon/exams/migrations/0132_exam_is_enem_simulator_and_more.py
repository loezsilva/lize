# Generated by Django 4.0.6 on 2023-09-13 14:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0131_alter_exam_category_alter_historicalexam_category'),
    ]

    operations = [
        migrations.AddField(
            model_name='exam',
            name='is_enem_simulator',
            field=models.BooleanField(blank=True, default=False, verbose_name='É um simulado Enem'),
        ),
        migrations.AddField(
            model_name='historicalexam',
            name='is_enem_simulator',
            field=models.BooleanField(blank=True, default=False, verbose_name='É um simulado Enem'),
        ),
    ]
