# Generated by Django 4.0.2 on 2022-04-20 20:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('omr', '0010_alter_omrerror_created_at_alter_omrerror_updated_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='omrerror',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Atualizado em'),
        ),
        migrations.AlterField(
            model_name='omrstudents',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Atualizado em'),
        ),
        migrations.AlterField(
            model_name='omrupload',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Atualizado em'),
        ),
    ]
