# Generated by Django 4.0.6 on 2022-10-24 19:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inspectors', '0024_inspector_can_annul'),
    ]

    operations = [
        migrations.AddField(
            model_name='teachersubject',
            name='is_abstract',
            field=models.BooleanField(default=False, verbose_name='Professor abstrato'),
        ),
    ]
