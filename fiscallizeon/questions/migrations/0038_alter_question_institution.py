# Generated by Django 4.0.4 on 2022-04-28 03:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0037_historicalquestion_adapted_question_adapted'),
    ]

    operations = [
        migrations.AlterField(
            model_name='question',
            name='institution',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='qtituição'),
        ),
    ]
