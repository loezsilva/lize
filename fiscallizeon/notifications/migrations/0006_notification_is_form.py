# Generated by Django 4.0.4 on 2022-04-22 17:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notifications', '0005_alter_notification_updated_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='notification',
            name='is_form',
            field=models.BooleanField(default=False, verbose_name='É um formulário'),
        ),
    ]
