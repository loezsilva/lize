# Generated by Django 3.2.4 on 2021-12-29 20:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0051_merge_0048_auto_20211127_1241_0050_auto_20211218_1146'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exam',
            name='is_abstract',
            field=models.BooleanField(default=False, verbose_name='A prova é abstrata, usada apenas na geração de gabarito avulso'),
        ),
        migrations.AlterField(
            model_name='historicalexam',
            name='is_abstract',
            field=models.BooleanField(default=False, verbose_name='A prova é abstrata, usada apenas na geração de gabarito avulso'),
        ),
    ]
