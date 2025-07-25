# Generated by Django 4.0.6 on 2022-11-25 23:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0058_alter_client_disable_stripped_answer_sheet'),
    ]

    operations = [
        migrations.AddField(
            model_name='examprintconfig',
            name='discursive_line_height',
            field=models.FloatField(default=1, help_text='Designa ao espaçamento entre linhas das respostas discursivas.', verbose_name='espaçamento entre linhas de respostas'),
        ),
        migrations.AddField(
            model_name='examprintconfig',
            name='font_family',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Plex Sans'), (1, 'Verdana'), (2, 'Times'), (3, 'Arial')], default=0, verbose_name='tipo da fonte'),
        ),
        migrations.AddField(
            model_name='examprintconfig',
            name='hide_questions_referencies',
            field=models.BooleanField(default=False, help_text='Designa se a caderno ocultar os textos referências das questões.', verbose_name='ocultar texto de referência das alternativas'),
        ),
        migrations.AlterField(
            model_name='examprintconfig',
            name='font_size',
            field=models.PositiveSmallIntegerField(choices=[(0, '12pt'), (1, '14pt'), (2, '18pt'), (3, '22pt'), (4, '32pt'), (5, '8pt'), (6, '10pt')], default=0, verbose_name='tamanho da fonte'),
        ),
    ]
