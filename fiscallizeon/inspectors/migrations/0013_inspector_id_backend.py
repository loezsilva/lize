# Generated by Django 3.2.4 on 2021-12-11 19:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inspectors', '0012_auto_20210923_1513'),
    ]

    operations = [
        migrations.AddField(
            model_name='inspector',
            name='id_backend',
            field=models.UUIDField(blank=True, null=True, verbose_name='Identificador no fiscallize presenial'),
        ),
    ]
