# Generated by Django 4.0.6 on 2023-03-24 19:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0085_merge_20230323_1924'),
    ]

    operations = [
        migrations.RenameField(
            model_name='clientteacherobligationconfiguration',
            old_name='bncc',
            new_name='abilities',
        ),
    ]
