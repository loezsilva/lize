# Generated by Django 3.2.4 on 2022-01-27 17:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('classes', '0009_alter_schoolclass_school_year'),
        ('materials', '0005_alter_studymaterial_material'),
    ]

    operations = [
        migrations.AddField(
            model_name='studymaterial',
            name='grades',
            field=models.ManyToManyField(blank=True, to='classes.Grade', verbose_name='Turmas'),
        ),
    ]
