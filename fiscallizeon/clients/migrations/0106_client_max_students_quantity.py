# Generated by Django 4.0.6 on 2023-09-24 03:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0105_client_has_sisu_simulator'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='max_students_quantity',
            field=models.SmallIntegerField(blank=True, null=True, verbose_name='Quantidade máxima de alunos'),
        ),
    ]
