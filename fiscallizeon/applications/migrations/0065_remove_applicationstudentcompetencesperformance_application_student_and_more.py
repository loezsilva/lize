# Generated by Django 4.0.2 on 2022-07-11 12:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0064_merge_20220628_1200'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='applicationstudentcompetencesperformance',
            name='application_student',
        ),
        migrations.RemoveField(
            model_name='applicationstudentcompetencesperformance',
            name='competence',
        ),
        migrations.RemoveField(
            model_name='applicationstudenttopicperformance',
            name='application_student',
        ),
        migrations.RemoveField(
            model_name='applicationstudenttopicperformance',
            name='topic',
        ),
        migrations.DeleteModel(
            name='ApplicationStudentAbilitiesPerformance',
        ),
        migrations.DeleteModel(
            name='ApplicationStudentCompetencesPerformance',
        ),
        migrations.DeleteModel(
            name='ApplicationStudentTopicPerformance',
        ),
    ]
