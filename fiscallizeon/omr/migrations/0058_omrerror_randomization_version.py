# Generated by Django 4.0.6 on 2024-04-26 17:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('omr', '0057_alter_omrdiscursivescan_image_hash'),
    ]

    operations = [
        migrations.AddField(
            model_name='omrerror',
            name='randomization_version',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Versão da randomização'),
        ),
    ]
