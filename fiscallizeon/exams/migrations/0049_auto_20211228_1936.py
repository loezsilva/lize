# Generated by Django 3.2.4 on 2021-12-28 22:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0048_auto_20211127_1241'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exam',
            name='is_abstract',
            field=models.BooleanField(default=False, verbose_name='É abstrata'),
        ),
        migrations.AlterField(
            model_name='historicalexam',
            name='is_abstract',
            field=models.BooleanField(default=False, verbose_name='É abstrata'),
        ),
    ]
