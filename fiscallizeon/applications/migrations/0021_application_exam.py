# Generated by Django 3.0.7 on 2020-10-29 19:27

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0001_initial'),
        ('applications', '0020_auto_20200925_1611'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='exam',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='exams.Exam', verbose_name='Prova'),
        ),
    ]
