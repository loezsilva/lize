# Generated by Django 4.0.6 on 2023-03-07 13:37

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0076_confignotification'),
    ]

    operations = [
        migrations.AlterField(
            model_name='confignotification',
            name='client',
            field=models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, to='clients.client', verbose_name='Cliente'),
        ),
    ]
