# Generated by Django 4.0.6 on 2023-08-09 19:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0084_merge_20230710_1551'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='end_last_answer_sheet_generation',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Data final da última geração de gabarito'),
        ),
    ]
