# Generated by Django 3.2.4 on 2022-01-06 22:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0027_client_id_erp'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='client',
            name='id_erp',
        ),
        migrations.AddField(
            model_name='unity',
            name='id_erp',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='ID ERP'),
        ),
    ]
