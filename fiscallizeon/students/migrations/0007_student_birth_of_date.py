# Generated by Django 4.0.2 on 2022-02-24 16:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0006_student_id_erp'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='birth_of_date',
            field=models.DateField(blank=True, null=True, verbose_name='Data de nascimento'),
        ),
    ]
