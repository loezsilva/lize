# Generated by Django 3.2.3 on 2021-07-21 20:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('classes', '0006_auto_20210126_1340'),
        ('inspectors', '0009_inspector_is_discipline_coordinator'),
        ('analytics', '0003_classsubjectapplicationlevel_level'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='classsubjectapplicationlevel',
            unique_together={('date', 'teacher_subject', 'school_class', 'level')},
        ),
    ]
