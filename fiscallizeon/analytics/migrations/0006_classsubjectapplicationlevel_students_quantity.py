# Generated by Django 3.2.3 on 2021-07-22 21:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0005_auto_20210722_1417'),
    ]

    operations = [
        migrations.AddField(
            model_name='classsubjectapplicationlevel',
            name='students_quantity',
            field=models.PositiveSmallIntegerField(default=1),
        ),
    ]
