# Generated by Django 4.0.6 on 2022-12-12 21:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0108_merge_20221127_1104'),
    ]

    operations = [
        migrations.AddField(
            model_name='examquestion',
            name='short_code',
            field=models.CharField(blank=True, max_length=10, null=True, verbose_name='Código de indetificação curto'),
        ),
        migrations.AddField(
            model_name='historicalexamquestion',
            name='short_code',
            field=models.CharField(blank=True, max_length=10, null=True, verbose_name='Código de indetificação curto'),
        ),
    ]
