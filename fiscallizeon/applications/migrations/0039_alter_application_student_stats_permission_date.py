# Generated by Django 3.2.4 on 2021-10-04 17:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0038_auto_20210913_1535'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='student_stats_permission_date',
            field=models.DateField(blank=True, null=True, verbose_name='Data para liberação dos resultados para os alunos'),
        ),
    ]
