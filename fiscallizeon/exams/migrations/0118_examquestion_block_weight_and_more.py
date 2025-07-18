# Generated by Django 4.0.6 on 2023-04-19 18:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0117_alter_exam_total_grade_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='examquestion',
            name='block_weight',
            field=models.BooleanField(default=False, verbose_name='Bloquear peso da questão'),
        ),
        migrations.AddField(
            model_name='examteachersubject',
            name='block_subject_note',
            field=models.BooleanField(default=False, verbose_name='Bloquear nota do professor'),
        ),
        migrations.AddField(
            model_name='historicalexamquestion',
            name='block_weight',
            field=models.BooleanField(default=False, verbose_name='Bloquear peso da questão'),
        ),
        migrations.AddField(
            model_name='historicalexamteachersubject',
            name='block_subject_note',
            field=models.BooleanField(default=False, verbose_name='Bloquear nota do professor'),
        ),
    ]
