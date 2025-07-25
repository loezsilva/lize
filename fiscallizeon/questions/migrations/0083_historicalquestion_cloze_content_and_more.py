# Generated by Django 4.2.19 on 2025-07-08 17:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('questions', '0082_historicalquestion_break_alternatives_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalquestion',
            name='cloze_content',
            field=models.CharField(blank=True, help_text='Utilize o formato [[opção]] para definir lacunas.', max_length=1000, null=True, verbose_name='Conteúdo da questão de preenchimento de lacunas'),
        ),
        migrations.AddField(
            model_name='historicalquestion',
            name='incorrect_cloze_alternatives',
            field=models.CharField(blank=True, help_text='Informe as alternativas separadas por vírgula.', max_length=1000, null=True, verbose_name='Alternativas incorretas da questão de preenchimento de lacunas'),
        ),
        migrations.AddField(
            model_name='question',
            name='cloze_content',
            field=models.CharField(blank=True, help_text='Utilize o formato [[opção]] para definir lacunas.', max_length=1000, null=True, verbose_name='Conteúdo da questão de preenchimento de lacunas'),
        ),
        migrations.AddField(
            model_name='question',
            name='incorrect_cloze_alternatives',
            field=models.CharField(blank=True, help_text='Informe as alternativas separadas por vírgula.', max_length=1000, null=True, verbose_name='Alternativas incorretas da questão de preenchimento de lacunas'),
        ),
        migrations.AlterField(
            model_name='historicalquestion',
            name='category',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Discursiva'), (1, 'Objetiva'), (2, 'Arquivo anexado'), (3, 'Somatório'), (4, 'Preencher lacunas')], default=1, verbose_name='Tipo da questão'),
        ),
        migrations.AlterField(
            model_name='question',
            name='category',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Discursiva'), (1, 'Objetiva'), (2, 'Arquivo anexado'), (3, 'Somatório'), (4, 'Preencher lacunas')], default=1, verbose_name='Tipo da questão'),
        ),
    ]
