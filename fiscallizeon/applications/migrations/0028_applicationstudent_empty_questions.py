# Generated by Django 3.0.7 on 2021-04-30 21:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0027_auto_20210225_1947'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicationstudent',
            name='empty_questions',
            field=models.PositiveIntegerField(default=0, verbose_name='Questões em branco'),
        ),
    ]
