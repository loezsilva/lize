# Generated by Django 4.0.6 on 2022-10-24 19:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0097_examteachersubject_is_abstract_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='examteachersubject',
            name='is_abstract',
        ),
        migrations.RemoveField(
            model_name='historicalexamteachersubject',
            name='is_abstract',
        ),
    ]
