# Generated by Django 4.0.6 on 2024-07-24 12:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0135_client_has_dashboards'),
    ]

    operations = [
        migrations.AddField(
            model_name='client',
            name='has_filtered_layout_for_today_student_applications',
            field=models.BooleanField(default=False, verbose_name='Possui layout com filtros e divisão para aplicações do dia no painel de aluno'),
        ),
    ]
