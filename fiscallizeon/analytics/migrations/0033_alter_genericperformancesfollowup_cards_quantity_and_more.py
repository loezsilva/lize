# Generated by Django 4.0.6 on 2023-09-25 13:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0032_remove_genericperformancesfollowup_type_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='genericperformancesfollowup',
            name='cards_quantity',
            field=models.IntegerField(default=0, verbose_name='Pendências total cartões'),
        ),
        migrations.AlterField(
            model_name='genericperformancesfollowup',
            name='cards_total',
            field=models.IntegerField(default=0, verbose_name='Total cartões'),
        ),
    ]
