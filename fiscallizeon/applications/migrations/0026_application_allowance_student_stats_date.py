# Generated by Django 3.0.7 on 2021-02-25 19:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('applications', '0025_merge_20210221_2008'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='allowance_student_stats_date',
            field=models.DateField(blank=True, help_text='Deixe este campo em branco se deseja que o aluno veja o resultado da prova após o final da aplicação', null=True, verbose_name='Data para liberação dos resultados para os alunos'),
        ),
    ]
