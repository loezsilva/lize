# Generated by Django 4.0.6 on 2023-06-13 23:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0016_alter_notification_options_alter_notification_model'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='delay',
            field=models.SmallIntegerField(default=1, verbose_name='Delay para mostrar a modal'),
        ),
    ]
