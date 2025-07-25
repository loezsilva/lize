# Generated by Django 4.0.2 on 2022-04-07 03:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('exams', '0076_merge_20220406_1458'),
    ]

    operations = [
        migrations.AlterField(
            model_name='exam',
            name='group_attachments',
            field=models.BooleanField(default=False, help_text='Ativa esta opção se deseja que os alunos envie as respostas de anexo agrupadas ao final de cada disciplina.', verbose_name='Agrupar anexos'),
        ),
        migrations.AlterField(
            model_name='exam',
            name='is_abstract',
            field=models.BooleanField(default=False, verbose_name='O caderno é abstrato, usada apenas na geração de gabarito avulso'),
        ),
        migrations.AlterField(
            model_name='exam',
            name='is_english_spanish',
            field=models.BooleanField(default=False, help_text='Ative esta opção se deseja que o aluno selecione uma língua estrangeira para realizar a prova', verbose_name='Caderno com língua estrangeira'),
        ),
        migrations.AlterField(
            model_name='historicalexam',
            name='group_attachments',
            field=models.BooleanField(default=False, help_text='Ativa esta opção se deseja que os alunos envie as respostas de anexo agrupadas ao final de cada disciplina.', verbose_name='Agrupar anexos'),
        ),
        migrations.AlterField(
            model_name='historicalexam',
            name='is_abstract',
            field=models.BooleanField(default=False, verbose_name='O caderno é abstrato, usada apenas na geração de gabarito avulso'),
        ),
        migrations.AlterField(
            model_name='historicalexam',
            name='is_english_spanish',
            field=models.BooleanField(default=False, help_text='Ative esta opção se deseja que o aluno selecione uma língua estrangeira para realizar a prova', verbose_name='Caderno com língua estrangeira'),
        ),
    ]
