# Generated by Django 4.0.6 on 2023-04-13 22:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0091_questiontag_is_question_correction_tag'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='questiontag',
            name='is_question_correction_tag',
        ),
        migrations.AddField(
            model_name='questiontag',
            name='type',
            field=models.PositiveIntegerField(choices=[(0, 'Para revisão'), (1, 'Para edição')], default=0, verbose_name='tipo'),
        ),
    ]
