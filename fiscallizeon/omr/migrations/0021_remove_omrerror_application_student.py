# Generated by Django 4.0.6 on 2022-10-25 18:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('omr', '0020_alter_omrcategory_options'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='omrerror',
            name='application_student',
        ),
    ]
