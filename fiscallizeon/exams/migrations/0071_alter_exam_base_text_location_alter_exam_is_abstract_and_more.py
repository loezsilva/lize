# Generated by Django 4.0.2 on 2022-03-21 22:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0070_merge_20220321_1647'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exam',
            name='base_text_location',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Textos base por questão'), (1, 'Textos base por disciplina'), (2, 'Textos base no início do caderno'), (3, 'Textos base no final do caderno')], default=0, verbose_name='Posição dos textos'),
        ),
        migrations.AlterField(
            model_name='exam',
            name='is_abstract',
            field=models.BooleanField(default=False, verbose_name='O exame é apenas para gabarito? '),
        ),
        migrations.AlterField(
            model_name='exam',
            name='is_english_spanish',
            field=models.BooleanField(default=False, help_text='Marque esta opção se este caderno inicia com 5 questões de ingês e 5 de espanhol', verbose_name='Tem língua estrangeira'),
        ),
        migrations.AlterField(
            model_name='historicalexam',
            name='base_text_location',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Textos base por questão'), (1, 'Textos base por disciplina'), (2, 'Textos base no início do caderno'), (3, 'Textos base no final do caderno')], default=0, verbose_name='Posição dos textos'),
        ),
        migrations.AlterField(
            model_name='historicalexam',
            name='is_abstract',
            field=models.BooleanField(default=False, verbose_name='O exame é apenas para gabarito? '),
        ),
        migrations.AlterField(
            model_name='historicalexam',
            name='is_english_spanish',
            field=models.BooleanField(default=False, help_text='Marque esta opção se este caderno inicia com 5 questões de ingês e 5 de espanhol', verbose_name='Tem língua estrangeira'),
        ),
    ]
