# Generated by Django 4.0.6 on 2023-10-09 13:45

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0132_exam_is_enem_simulator_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='examteachersubject',
            unique_together={('exam', 'order')},
        ),
    ]