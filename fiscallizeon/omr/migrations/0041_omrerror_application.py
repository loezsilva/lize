# Generated by Django 4.0.6 on 2023-07-20 16:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0083_merge_20230710_1439'),
        ('omr', '0040_omrupload_seen'),
    ]

    operations = [
        migrations.AddField(
            model_name='omrerror',
            name='application',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='applications.application', verbose_name='Aplicação'),
        ),
    ]
