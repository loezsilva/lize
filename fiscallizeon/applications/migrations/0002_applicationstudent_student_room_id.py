# Generated by Django 3.0.7 on 2020-06-13 20:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='applicationstudent',
            name='student_room_id',
            field=models.IntegerField(blank=True, help_text='Código do aluno na sala', null=True, verbose_name='Código do aluno na sala'),
        ),
    ]
