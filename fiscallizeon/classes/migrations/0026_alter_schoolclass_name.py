# Generated by Django 4.0.6 on 2024-03-06 18:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('classes', '0025_alter_schoolclass_unique_together'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schoolclass',
            name='name',
            field=models.CharField(db_index=True, max_length=250, verbose_name='Nome'), 
        ),
    ]
