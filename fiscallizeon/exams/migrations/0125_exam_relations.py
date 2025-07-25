# Generated by Django 4.0.6 on 2023-06-15 17:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subjects', '0020_subjectrelation'),
        ('exams', '0124_exam_related_subjects_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='exam',
            name='relations',
            field=models.ManyToManyField(blank=True, to='subjects.subjectrelation', verbose_name='Disciplinas relacionadas'),
        ),
    ]
