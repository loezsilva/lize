# Generated by Django 4.0.6 on 2022-11-22 18:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0104_alter_exam_stage_alter_historicalexam_stage'),
    ]

    operations = [
        migrations.AddField(
            model_name='examteachersubject',
            name='elaboration_email_sent',
            field=models.BooleanField(default=False, verbose_name='O email de elaboração foi enviado'),
        ),
        migrations.AddField(
            model_name='historicalexamteachersubject',
            name='elaboration_email_sent',
            field=models.BooleanField(default=False, verbose_name='O email de elaboração foi enviado'),
        ),
    ]
