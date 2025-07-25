# Generated by Django 4.0.2 on 2022-07-22 03:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('corrections', '0001_initial'),
        ('answers', '0035_historicalretryanswer'),
    ]

    operations = [
        migrations.AddField(
            model_name='fileanswer',
            name='correction_file_answer',
            field=models.ManyToManyField(blank=True, through='corrections.CorrectionFileAnswer', to='corrections.CorrectionCriterion', verbose_name='Correções'),
        ),
        migrations.AddField(
            model_name='textualanswer',
            name='correction_textual_answer',
            field=models.ManyToManyField(through='corrections.CorrectionTextualAnswer', to='corrections.CorrectionCriterion', verbose_name='Correção textual'),
        ),
    ]
