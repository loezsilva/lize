# Generated by Django 3.0.7 on 2020-10-29 19:27

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('exams', '0001_initial'),
        ('questions', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='exam',
            name='questions',
            field=models.ManyToManyField(to='questions.Question', verbose_name='Questões'),
        ),
    ]
