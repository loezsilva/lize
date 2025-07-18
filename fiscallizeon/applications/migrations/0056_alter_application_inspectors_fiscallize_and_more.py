# Generated by Django 4.0.2 on 2022-05-04 16:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0055_merge_20220502_2118'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='inspectors_fiscallize',
            field=models.BooleanField(default=False, help_text='Marque essa opção se deseja um fiscal Fiscallize', verbose_name='Fiscais da Fiscallize'),
        ),
        migrations.AlterField(
            model_name='randomizationversion',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Registrado em'),
        ),
    ]
