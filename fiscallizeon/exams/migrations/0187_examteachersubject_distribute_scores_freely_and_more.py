# Generated by Django 4.0.6 on 2024-10-08 19:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0186_alter_exam_copy_exam_with_ia_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='examteachersubject',
            name='distribute_scores_freely',
            field=models.BooleanField(default=False, verbose_name='Permitir o professor distribuir pontuação livremente'),
        ),
        migrations.AddField(
            model_name='historicalexamteachersubject',
            name='distribute_scores_freely',
            field=models.BooleanField(default=False, verbose_name='Permitir o professor distribuir pontuação livremente'),
        ),
    ]
