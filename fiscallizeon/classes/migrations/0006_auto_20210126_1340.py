# Generated by Django 3.0.7 on 2021-01-26 16:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('students', '0003_auto_20201212_1524'),
        ('classes', '0005_auto_20210126_1338'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schoolclass',
            name='grade_old',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='Série antiga'),
        ),
        migrations.AlterField(
            model_name='schoolclass',
            name='students',
            field=models.ManyToManyField(blank=True, help_text='Selecione acima os alunos que fazem parte dessa turma', related_name='classes', to='students.Student', verbose_name='Alunos dessa turma'),
        ),
    ]
