# Generated by Django 4.0.6 on 2024-03-29 14:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0161_merge_20240329_1124'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='historicalexam',
            options={'get_latest_by': 'history_date', 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'historical Caderno'},
        ),
        migrations.AlterModelOptions(
            name='historicalexamquestion',
            options={'get_latest_by': 'history_date', 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'historical Questão na prova'},
        ),
        migrations.AlterModelOptions(
            name='historicalexamteachersubject',
            options={'get_latest_by': 'history_date', 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'historical Professor na prova'},
        ),
        migrations.AlterField(
            model_name='historicalexam',
            name='history_date',
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name='historicalexamquestion',
            name='history_date',
            field=models.DateTimeField(),
        ),
        migrations.AlterField(
            model_name='historicalexamteachersubject',
            name='history_date',
            field=models.DateTimeField(),
        ),
    ]
