# Generated by Django 4.0.6 on 2023-02-14 14:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('omr', '0033_omrcategory_column_discursives_count_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='omrcategory',
            name='discursive_grade_setps',
            field=models.PositiveSmallIntegerField(default=5, verbose_name='Número de possibilidades de nota discussiva'),
        ),
        migrations.AlterField(
            model_name='omrcategory',
            name='is_discursive',
            field=models.BooleanField(default=False, verbose_name='É modelo discussivo?'),
        ),
    ]
