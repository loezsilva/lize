# Generated by Django 4.0.2 on 2022-04-20 20:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('classes', '0011_alter_grade_created_at_alter_grade_updated_at_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='grade',
            name='level',
            field=models.PositiveIntegerField(choices=[(0, 'Ensino Médio'), (1, 'Ensino Fundamental')], db_index=True, verbose_name='Ensino'),
        ),
        migrations.AlterField(
            model_name='grade',
            name='name',
            field=models.CharField(db_index=True, max_length=50, verbose_name='Nome'),
        ),
        migrations.AlterField(
            model_name='grade',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Atualizado em'),
        ),
        migrations.AlterField(
            model_name='schoolclass',
            name='name',
            field=models.CharField(db_index=True, max_length=50, verbose_name='Nome'),
        ),
        migrations.AlterField(
            model_name='schoolclass',
            name='school_year',
            field=models.SmallIntegerField(blank=True, db_index=True, default='2022', verbose_name='Ano letivo da turma'),
        ),
        migrations.AlterField(
            model_name='schoolclass',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, verbose_name='Atualizado em'),
        ),
    ]
