# Generated by Django 3.2.4 on 2021-10-26 17:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('omr', '0008_alter_omrupload_processing_log'),
    ]

    operations = [
        migrations.AlterField(
            model_name='omrupload',
            name='total_pages',
            field=models.PositiveSmallIntegerField(default=0, verbose_name='Páginas lidas com sucesso'),
        ),
    ]
