# Generated by Django 4.0.6 on 2024-02-28 17:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0095_applicationrandomizationversion_and_more'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='applicationrandomizationversion',
            unique_together={('application', 'version_number', 'sequential')},
        ),
    ]
